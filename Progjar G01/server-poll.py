import socket
import select
import os
import sys

HOST = '127.0.0.1'
PORT = 5000
BUFFER_SIZE = 4096
SERVER_DIR = "server_files"
os.makedirs(SERVER_DIR, exist_ok=True)

def start_poll_server():
    # Linux only
    if sys.platform == "win32":
        print("ERROR: The 'select.poll()' module is NOT supported on Windows!")
        print("Please run this specific file on Linux, macOS, or WSL.")
        return

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    
    print(f"[POLL SERVER] Listening on {HOST}:{PORT}")
    
    fd_to_socket = {server_socket.fileno(): server_socket}
    client_addrs = {}
    clients = []
    
    poller = select.poll()
    poller.register(server_socket, select.POLLIN)
    
    def broadcast(message, sender_socket=None):
        for client in clients:
            if client != sender_socket:
                try:
                    client.sendall(message)
                except:
                    pass

    while True:
        events = poller.poll()
        
        for fd, flag in events:
            s = fd_to_socket[fd]
            
            # POLLIN means there is data to read
            if flag & (select.POLLIN | select.POLLPRI):
                if s is server_socket:
                    client_socket, addr = s.accept()
                    print(f"[+] Client connected from {addr}")
                    fd_to_socket[client_socket.fileno()] = client_socket
                    client_addrs[client_socket] = addr
                    clients.append(client_socket)
                    poller.register(client_socket, select.POLLIN)
                else:
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
                            poller.unregister(s)
                            del fd_to_socket[fd]
                            if s in clients: clients.remove(s)
                            s.close()
                            broadcast(f"MSG|Client [{addr[1]}] disconnected.".encode('utf-8'))
                    except Exception as e:
                        print(f"[-] Error with client {addr}: {e}")
                        poller.unregister(s)
                        del fd_to_socket[fd]
                        if s in clients: clients.remove(s)
                        s.close()

if __name__ == "__main__":
    start_poll_server()