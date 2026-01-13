import socket
import json
import time

HOST = '0.0.0.0'
PORT = 5001

clients = {}

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #Cria socket, UDP sempre usa SOCK_DGRAM.
s.bind((HOST, PORT)) #Faz o Bind, associa o socket ao host e porta 5001
print(f"[START] servidor UDP on {HOST}:{PORT}")

# Variável para rastrear o benchmark (apenas para a lógica de timeout)
pending_benchmarks = {} 


#Loop infinito recebendo mensagens
while True:
    try: 
        # Tenta receber dados e endereço. O erro 10054 pode ocorrer aqui.
        try:
            data, addr = s.recvfrom(65536) 
        except Exception as e:
            # Tratamento da falha do Windows
            if "10054" in str(e) or "forcado o cancelamento" in str(e):
                print(f"[ERRO CRITICO ISOLADO] Socket fechado, tentando reiniciar a escuta: [WinError 10054] {e}")
                continue # Volta ao início do while True para tentar receber mais
            else:
                raise # Se for outro erro, lançamos para o except externo

        # Continuação normal se o recvfrom foi bem-sucedido
        text = data.decode('utf-8', errors='ignore').strip() 

        # Registrar cliente novo
        if addr not in clients:
            clients[addr] = f"{addr[0]}:{addr[1]}"
            print(f"[NOVO CLIENTE UDP] {addr}")
            s.sendto(f"[Servidor] Seu nick agora é: {clients[addr]}".encode(), addr) 

        nick = clients.get(addr, f"{addr[0]}:{addr[1]}")

        if text.startswith('/bench_start:'):
            try:
                n = int(text.split(':')[1].strip())
                pending_benchmarks[addr] = {'expected': n, 'received': 0, 'start_time': time.time()}
                print(f"[UDP BENCH] Recebido comando START de {nick}. Esperando {n} bytes...")
                s.sendto(f"[Servidor] Prontidão para receber {n} bytes.".encode(), addr)
            except Exception as e:
                print(f"[ERRO BENCH START] {e}")
            continue

        if text.startswith('/bench_end:'):
            if addr in pending_benchmarks:
                data = pending_benchmarks.pop(addr)
                elapsed = time.time() - data['start_time']
                received = data['received']
                
                print(f"[UDP BENCH] Recebido comando END de {nick}. Recebeu {received} bytes em {elapsed:.4f}s.")
                s.sendto(f"[Servidor] Teste de Benchmark Concluído. Tempo: {elapsed:.4f}s. Recebidos {received} bytes.".encode(), addr)
            continue
            
        if addr in pending_benchmarks:
            # Se a mensagem não é um comando e estamos esperando dados, tratamos como payload
            pending_benchmarks[addr]['received'] += len(data)
            continue # Não retransmite o payload como chat!

        
        if text.startswith('/nick '):
            newnick = text.split(' ',1)[1].strip()
            clients[addr] = newnick or clients[addr]
            reply = f"Seu nick agora é: {clients[addr]}"
            s.sendto(reply.encode(), addr)
            print(f"[NICK] {addr} -> {clients[addr]}")
            continue
        
        if text.startswith('/sair'): # comando de desconexão
            print(f"[ DESCONECTAR UDP] {addr} nick={clients.get(addr)}")
            clients.pop(addr, None)
            continue

        # Se o texto não for um comando, é mensagem comum: retransmite
        outgoing = f"{nick}: {text}"
        print(f"[MSG UDP] {outgoing}")
        for c in list(clients):
            if c != addr:
                try:
                    s.sendto(outgoing.encode(), c)
                except Exception:
                    clients.pop(c, None)

    except KeyboardInterrupt:
        break
    except Exception as e:
        # Erro genérico no processamento, que não é o 10054
        print(f"[ERRO GENÉRICO NO LOOP] {e}")
        continue # Continua o loop

print("[FINALIZANDO] Servidor UDP encerrado.")
s.close()