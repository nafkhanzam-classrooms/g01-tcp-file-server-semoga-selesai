import socket
import select
import os

HOST = '127.0.0.1'
PORT = 5000
BUFFER_SIZE = 4096
SERVER_DIR = "server_files"
os.makedirs(SERVER_DIR, exist_ok=True)

def start_select_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    
    inputs = [server_socket]
    clients = []
    client_addrs = {}

    print(f"[SELECT SERVER] Listening on {HOST}:{PORT}")

    def broadcast(message, sender_socket=None):
        for client in clients:
            if client != sender_socket:
                try:
                    client.sendall(message)
                except:
                    pass

    while inputs:
        # select() blocks until at least one socket in 'inputs' has activity
        readable, _, _ = select.select(inputs, [], inputs)
        
        for s in readable:
            if s is server_socket:
                # Activity on the main server socket means a new connection
                client_socket, addr = s.accept()
                print(f"[+] Client connected from {addr}")
                inputs.append(client_socket)
                clients.append(client_socket)
                client_addrs[client_socket] = addr
            else:
                # Activity on a client socket means they sent us a message/file
                addr = client_addrs.get(s, ("Unknown", 0))
                try:
                    data = s.recv(BUFFER_SIZE).decode('utf-8')
                    if data:
                        if data.startswith("CHAT|"):
                            msg = data[5:]
                            print(f"[{addr}] Chat: {msg}")
                            broadcast(f"MSG|[{addr[1]}] {msg}".encode('utf-8'), s)
                        
                        elif data.startswith("CMD|/list"):
                            files = os.listdir(SERVER_DIR)
                            file_list = "\n".join(files) if files else "No files on server."
                            s.sendall(f"MSG|Server Files:\n{file_list}".encode('utf-8'))
                            
                        elif data.startswith("CMD|/upload"):
                            _, _, filename, filesize = data.split('|')
                            filesize = int(filesize)
                            print(f"[{addr}] Uploading {filename} ({filesize} bytes)...")
                            
                            bytes_received = 0
                            filepath = os.path.join(SERVER_DIR, filename)
                            with open(filepath, 'wb') as f:
                                while bytes_received < filesize:
                                    chunk = s.recv(min(BUFFER_SIZE, filesize - bytes_received))
                                    if not chunk: break
                                    f.write(chunk)
                                    bytes_received += len(chunk)
                            s.sendall(f"MSG|Server successfully received {filename}.".encode('utf-8'))
                            broadcast(f"MSG|[{addr[1]}] uploaded {filename}.".encode('utf-8'), s)
                            
                        elif data.startswith("CMD|/download"):
                            parts = data.split(' ')
                            if len(parts) > 1:
                                filename = parts[1]
                                filepath = os.path.join(SERVER_DIR, filename)
                                
                                if os.path.exists(filepath):
                                    filesize = os.path.getsize(filepath)
                                    s.sendall(f"FILE|{filename}|{filesize}".encode('utf-8'))
                                    ready_msg = s.recv(BUFFER_SIZE)
                                    if ready_msg == b"READY":
                                        with open(filepath, 'rb') as f:
                                            while (chunk := f.read(BUFFER_SIZE)):
                                                s.sendall(chunk)
                                else:
                                    s.sendall(f"MSG|Error: File '{filename}' not found.".encode('utf-8'))
                    else:
                        print(f"[-] Client {addr} disconnected.")
                        if s in inputs: inputs.remove(s)
                        if s in clients: clients.remove(s)
                        s.close()
                        broadcast(f"MSG|Client [{addr[1]}] disconnected.".encode('utf-8'))
                except Exception as e:
                    print(f"[-] Error with client {addr}: {e}")
                    if s in inputs: inputs.remove(s)
                    if s in clients: clients.remove(s)
                    s.close()

if __name__ == "__main__":
    start_select_server()