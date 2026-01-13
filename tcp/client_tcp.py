import socket
import threading
import sys
import time

HOST = "127.0.0.1"
PORT = 5000

def recv_loop(sock, running_flag): #thread que recebe mensagens do servidor e printa na tela
    try:
        while running_flag["running"]:
            try:
                # Recebe dados
                data = sock.recv(4096)
                
            except OSError: #socket fechado externamente
                break
                
            if not data:
                print("\n conexão encerrada pelo servidor")
                running_flag["running"] = False
                break
                
            # Tenta decodificar e imprimir
            try:
                text = data.decode("utf-8")
                if text.startswith("[Servidor] Teste de Benchmark Concluído."):
                    print(f"\n{text.strip()}")
                else:
                    # Mensagem de chat comum
                    print(text.rstrip("\n"))
                    
            except UnicodeDecodeError:
                text = repr(data)
                print(text.rstrip("\n"))
                
    except Exception as e:
        print(f"\n[recv] erro: {e}")
        running_flag["running"] = False


def main(): 
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # cria um socket tcp ipv4
    try:
        sock.connect((HOST, PORT)) #tenta conectar ao servidor
    except Exception as e:
        print(f"Erro ao conectar em {HOST}:{PORT}; {e}")
        return
    

    print(f"conectado a {HOST}:{PORT}. digite /nick <nome> para escolher seu nome, /sair para encerrar")

    running = {"running": True}

    # Solicita o nick inicial
    initial_nick = input("Digite seu Nickname inicial: ")
    if initial_nick.strip():
        # Usa o comando /nick para configurar o nome no servidor
        try:
            sock.sendall(f"/nick {initial_nick}\n".encode("utf-8"))
        except:
            pass
        nick = initial_nick
    else:
        # nick local (mostrado antes das mensagens que o usuário envia)
        nick = f"{sock.getsockname()[0]}:{sock.getsockname()[1]}" #usa seu ip:porta ate escolher um nick
    
    
    # inicia thread de recebimento
    t = threading.Thread(target=recv_loop, args=(sock, running), daemon=True) #cria e inicia a thread que ficara recebendo mensagens do servidor 
    t.start()
    
    try:
        while running["running"]:
            try:
                # Modificado para mostrar o nick no prompt
                line = input(f"Voce ({nick}): ")
            except EOFError:# ctrl d ou input fechado
                line = "/sair"
            except KeyboardInterrupt: #ctrl c
                line = "/sair"
                
            # Verifica se o loop de recebimento encerrou
            if not running["running"]: 
                break 
                
            line = line.strip()
                
            if line.startswith("/nick "): #comando /nick
                newnick = line[6:].strip()
                if newnick == "":
                    print("[system] nick inválido. Use: /nick SeuNome")
                    continue
                    
                # atualiza nick local e avisa o servidor
                nick = newnick
                try:
                    # Envia o comando /nick para o servidor
                    sock.sendall(f"/nick {nick}\n".encode("utf-8"))
                except Exception as e:
                    print(f" erro enviando /nick: {e}")
                    running["running"] = False
                    break
                print(f" seu nick agora é: {nick}")
                continue
                
            elif line.startswith("/bench "):
                try:
                    size_str = line.split(+ 1)[1].strip()
                    payload_size = int(size_str)
                    
                    if payload_size <= 0:
                         print("[ERRO] O tamanho deve ser um número positivo.")
                         continue
                         
                    print(f"\n[BENCHMARK] Iniciando teste TCP com {payload_size} bytes (aprox. {payload_size/1024/1024:.2f}MB)...")

                    # 1. Geracao do Payload
                    payload = '#' * payload_size
                    
                    start_time = time.time()
                    
                    header = f"/bench_start:{payload_size}:{start_time}\n" 
                    full_data_to_send = header + payload
                    
                    # 4. Envio (sendall garante que tudo sera enviado)-----------------
                    sock.sendall(full_data_to_send.encode('utf-8'))

                    print(f"[BENCHMARK] Envio de {payload_size} bytes concluído. Aguardando confirmação do servidor...")
                    
                except IndexError:
                    print("[ERRO] Comando /bench precisa de um argumento de tamanho (/bench <bytes>).")
                except ValueError:
                    print("[ERRO] O tamanho deve ser um número inteiro.")
                except Exception as e:
                    print(f"[ERRO] Falha no benchmark TCP: {e}")
                
                continue # Volta ao loop principal
            
            elif line == "/sair": # comando /sair
                try:
                    sock.sendall("/sair\n".encode("utf-8"))
                except:
                    pass
                running["running"] = False
                break
                
            
            to_send = line
            if to_send == "":
                continue
                
            
            print(f"[{nick}] {to_send}")
            try:
                sock.sendall((to_send + "\n").encode("utf-8")) #envia a mensagem ao servidor
            except Exception as e: #se tiver erro finaliza o cliente
                print(f"[system] erro enviando mensagem: {e}")
                running["running"] = False
                break
                
    finally:
        try:
            sock.close() #fecha o socket
        except:
            pass
        running["running"] = False #garante que running fique False pra recepcao de thread parar
        print("desconectado")

if __name__ == "__main__":
    main()