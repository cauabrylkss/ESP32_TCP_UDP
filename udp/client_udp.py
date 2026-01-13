import socket #comunicacao UDP
import threading #thread paralela para receber mensagens
import sys #le do teclado (stdin)
import time # mede tempo do /bench
import os # para sair do programa

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5001

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #Cria socket, UDP sempre usa SOCK_DGRAM.
s.bind(('', 0)) # Associa o socket a uma porta local

# Variável global para armazenar o nickname
NICKNAME = f"{s.getsockname()[0]}:{s.getsockname()[1]}"

# Funcao para enviar uma linha ao servidor
def send_line(line):
    s.sendto(line.encode(), (SERVER_HOST, SERVER_PORT))

# Thread para receber mensagens do servidor
def receive_loop():
    while True:
        try:
            data, addr = s.recvfrom(65536) #Recebe mensagens
            message = data.decode('utf-8')
            
            # --- Tratamento da Resposta do Benchmark ---
            if message.startswith("[Servidor] Teste de Benchmark Concluído."):
                print(f"\n{message.strip()}")
            else:
                # Mensagem normal ou resposta de comando
                sys.stdout.write('\n' + message.rstrip('\n') + '\n')
                sys.stdout.flush()
                
        except Exception as e: #Se der erro, sai do loop, a thred termina
            # print("Erro recv:", e) 
            break 

# Inicia a thread de recebimento
t = threading.Thread(target=receive_loop, daemon=True)
t.start()

# Loop principal para ler comandos do usuario
try:
    sys.stdout.write(f"Digite seu Nickname inicial (padrão: {NICKNAME}): ")
    sys.stdout.flush()
    initial_nick = sys.stdin.readline().rstrip('\n')
    
    if initial_nick:
        NICKNAME = initial_nick
    
    # Envia o nick para o servidor registrar
    send_line(f"/nick {NICKNAME}")

    while True:
        # Prompt de entrada (seguro com sys.stdin.readline)
        sys.stdout.write(f"Você ({NICKNAME}): ")
        sys.stdout.flush()
        
        line = sys.stdin.readline()
        
        if not line:
            line = "/sair"
            
        line = line.rstrip('\n')
        
        if line.startswith('/bench '): 
            try:
                # Extrai o tamanho total
                parts = line.split(' ', 1)
                n = int(parts[1])
            except IndexError:
                print("Uso: /bench <bytes>")
                continue
            except ValueError:
                print("Uso: /bench <bytes> - O valor deve ser um número.")
                continue

            send_line(f"/bench_start:{n}") 

            chunk = b'#' * 65536 # Usando # para consistência com o TCP
            tosend = n
            start = time.time()
           
            while tosend > 0: 
                sendnow = min(len(chunk), tosend)
                s.sendto(chunk[:sendnow], (SERVER_HOST, SERVER_PORT))
                tosend -= sendnow
                
                time.sleep(0.001) 
                
            elapsed = time.time() - start # tempo gasto para enviar tudo
            
            send_line(f"/bench_end:{n}") 
            
            print(f"[BENCHMARK] Enviados {n} bytes em {elapsed:.4f}s (client-side)")
            
            # Aguarda a resposta do servidor 
            continue
            
        # Tratamento de comandos /nick e /sair e mensagens
        
        if line.startswith('/nick '):
            newnick = line.split(' ', 1)[1].strip()
            if newnick:
                NICKNAME = newnick
                
        send_line(line) # Envia a linha para processamento no servidor

        if line.strip() == '/sair': #finaliza se digitar sair 
            break
            
except KeyboardInterrupt: #trata Ctrl+C (interrupcao do usuario)
    pass
finally: #Fecha o socket, finaliza o cliente UDP corretamente
    s.close()
    os._exit(0)