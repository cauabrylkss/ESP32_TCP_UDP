import socket
import threading
import datetime
import json #para passar mensagens estruturadas do esp 32
import time # NOVO: Necessário para medir o tempo do benchmark

HOST = '0.0.0.0' #significa que o servidor liga-se em todas interfaces de rede, ou seja, qqrl uma pode aceitar conexoes
PORT = 5000 # porta tcp onde o servidor vai escutar, msm do esp32

clients = [] #lista com infos de todos os clientes conectados {sock (objeto socket), addr (ip:port), name (do cliente) }
clients_lock = threading.Lock() #proteger operações (adicionar, remover, iterar) sob clients, pra previnir corrida entre os threads

def log(msg: str): #pra definir logs com o horario exato de chamada dele
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")

def broadcast(message: str, sender_sock=None): #envia a mensagem para todos os cliendes, menos sender_sock; se sender_sock for none envia para todos
    data = message.encode('utf-8') #converte a string pra bytes utf8
    with clients_lock: #garante que iterar, enviar, remover na lista clients seja thread-safe
        dead = [] #lista temporaria para sockets com erro (evita modificar clients[] enqnt itera)
        for c in clients: #iterando sob cada cliente
            sock = c["sock"]
            if sock is sender_sock: 
                continue #pular quem enviou

            try:
                sock.sendall(data) #enviar todos os bytes (se falhar é Exception)
            except Exception as e:
                log(f"Erro enviando para {c['addr']}: {e}")
                dead.append(c) #se falhar adiciona em dead[]  
        for d in dead:
            try:
                d["sock"].close() #fecha sockets mortos
            except:
                pass
            clients.remove(d) #remove da lista de clientes
            log(f"Removido cliente {d['addr']} após erro de envio")

def handle_client(client_sock: socket.socket, addr): #pra receber mensagens de um cliente e retransmitir
    name = f"{addr[0]}:{addr[1]}" #nome temporario a partir do ip e porta do cliente
    
    # Atualiza o nome inicial (se já tiver sido definido na aceitação)
    with clients_lock: 
        for c in clients:
            if c["sock"] is client_sock:
                # O nick será atualizado abaixo
                break
    
    log(f"Conexão de {name}")

    conectado = True
    
    # Variável para acumular dados incompletos
    buffer = ""

    try:
        while conectado:
            # Tenta receber um chunk de dados
            try:
                data = client_sock.recv(4096) 
            except OSError:
                break # Sai do loop se o socket fechar
                
            if not data:
                break # Conexão fechada pelo cliente

            # Decodifica e adiciona ao buffer
            try:
                text_chunk = data.decode('utf-8')
            except UnicodeDecodeError:
                text_chunk = repr(data) + '\n' # Trata erro, adiciona newline para forçar processamento
            
            buffer += text_chunk
            
            # Processa linha por linha no buffer
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                text = line.strip()
                
                if not text:
                    continue # Linha vazia

                # --- Lógica do Benchmark (Etapa 5) ---
                if text.startswith("/bench_start:"):
                    
                    try:
                        
                        parts = text.split(':')
                        original_size = int(parts[1])
                        start_time = float(parts[2].strip()) 

                        # O restante do buffer, após o '\n', é o início do payload
                        full_payload = buffer 
                        received_bytes = len(full_payload.encode('utf-8'))
                        
                        # Limpa o buffer para não processar o payload gigante como chat
                        buffer = ""

                        # Continua a receber bytes até atingir o tamanho esperado
                        while received_bytes < original_size:
                            # Recebe bytes crus, sem decodificar aqui, para maior eficiência e evitar problemas de codificação no meio
                            chunk_bytes = client_sock.recv(4096 * 10) 
                            if not chunk_bytes:
                                break
                            
                            full_payload += chunk_bytes.decode('utf-8', errors='ignore')
                            received_bytes = len(full_payload.encode('utf-8'))
                            
                        end_time = time.time()
                        duration = end_time - start_time
                        
                        log(f"[BENCHMARK] Payload de {received_bytes} bytes (esperado: {original_size}) recebido de {name}.")
                        log(f"[BENCHMARK] Duração: {duration:.4f} segundos.")
                        
                        # Envia a confirmação e resultados de volta para o cliente
                        client_sock.sendall(f"[Servidor] Teste de Benchmark Concluído. Tempo: {duration:.4f}s.\n".encode('utf-8'))
                        
                        # Volta ao loop para escutar novas mensagens (o benchmark foi concluído)
                        continue 
                        
                    except Exception as e:
                        log(f"[ERRO] Falha ao receber benchmark de {name}: {e}")
                        # Se falhar no benchmark, não continua o processamento de linha
                        continue
                
                
                if text == "/sair":
                    log(f"{name} pediu para sair.")
                    conectado = False
                    continue

                if text.startswith("/nick "):
                    newname = text[6:].strip()
                    if newname == "":
                        try:
                            client_sock.sendall("Nome inválido.\n".encode('utf-8'))
                        except:
                            pass
                        continue

                    old = name
                    with clients_lock:
                        for c in clients:
                            if c["sock"] is client_sock:
                                c["name"] = newname
                                name = newname
                                break
                    log(f"{old} mudou de nick para {newname}")
                    broadcast(f"[{old}] agora é [{newname}]\n", sender_sock=client_sock)
                    continue

                # Se não for um comando reconhecido, é mensagem comum
                log(f"Msg de {name}: {text}")
                broadcast(f"[{name}] {text}\n", sender_sock=client_sock)

            
    except ConnectionResetError:
        log(f"Conexão perdida com {name}.")
    except Exception as e:
        log(f"Erro com {name}: {e}")

    with clients_lock: #pra remover o cliente da lista
        to_remove = None #variavel que vai guardar dicionario do cliente a ser removido
        for c in clients:
            if c["sock"] is client_sock:
                to_remove = c
                break
        if to_remove:
            try:
                clients.remove(to_remove)
            except ValueError:
                pass
    
    try:
        client_sock.close()
    except:
        pass

    log(f"{name} desconectou.")
    broadcast(f"[{name}] saiu\n", sender_sock=None)

def accept_loop(server_sock: socket.socket): #func q vai aceitar novas conexoes nos server
    servidor_ativo = True
    while servidor_ativo:
        try:
            client_sock, addr = server_sock.accept()
        except Exception as e:
            log(f"Erro em accept(): {e}")
            servidor_ativo = False
            continue

        with clients_lock:
            clients.append({"sock": client_sock, "addr": addr, "name": f"{addr[0]}:{addr[1]}" })

        t = threading.Thread(target=handle_client, args=(client_sock, addr), daemon=True)
        t.start()
        log(f"Thread criada para {addr}; threads ativas: {threading.active_count()}")

def main():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #cria um socket tcp ipv4 
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #opcao para reutilizar endereco porta mais rapidamente
    server_sock.bind((HOST, PORT)) #associa o socket ao host e porta definidos no inicio
    server_sock.listen(10)
    log(f"Servidor TCP rodando em {HOST}:{PORT} — esperando conexões...")


    try:
        accept_loop(server_sock)
    except KeyboardInterrupt:
        log("Servidor interrompido por usuário (Ctrl+C).")
    finally:
        log("Fechando conexões...")
        with clients_lock:
            for c in clients:
                try:
                    c["sock"].close()
                except:
                    pass
            clients.clear()
        try:
            server_sock.close()
        except:
            pass
        log("Servidor finalizado.")

if __name__ == "__main__":
    main()
