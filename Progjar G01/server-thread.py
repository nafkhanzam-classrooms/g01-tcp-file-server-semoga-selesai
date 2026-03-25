import socket
import threading
import os

HOST = '127.0.0.1'
PORT = 5000
BUFFER_SIZE = 4096
SERVER_DIR = "server_files"
os.makedirs(SERVER_DIR, exist_ok=True)

# List semua yg connected, utk bc an
clients = []

def broadcast(message, sender_socket=None):
    """Send a message to all connected clients except the sender."""
    for client in clients:
        if client != sender_socket:
            try:
                client.sendall(message)
            except:
                pass

def handle_client(client_socket, addr):
    print(f"[+] Client connected from {addr}")
    clients.append(client_socket)
    
    try:
        while True:
            data = client_socket.recv(BUFFER_SIZE).decode('utf-8')
            if not data:
                break # Dc
            
            if data.startswith("CHAT|"):
                msg = data[5:]
                print(f"[{addr}] Chat: {msg}")
                # Forward chat ke semua
                broadcast(f"MSG|[{addr[1]}] {msg}".encode('utf-8'), client_socket)
            
            elif data.startswith("CMD|/list"):
                files = os.listdir(SERVER_DIR)
                file_list = "\n".join(files) if files else "No files on server."
                client_socket.sendall(f"MSG|Server Files:\n{file_list}".encode('utf-8'))
                
            elif data.startswith("CMD|/upload"):
                _, _, filename, filesize = data.split('|')
                filesize = int(filesize)
                print(f"[{addr}] Uploading {filename} ({filesize} bytes)...")
                
                bytes_received = 0
                filepath = os.path.join(SERVER_DIR, filename)
                with open(filepath, 'wb') as f:
                    while bytes_received < filesize:
                        chunk = client_socket.recv(min(BUFFER_SIZE, filesize - bytes_received))
                        if not chunk: break
                        f.write(chunk)
                        bytes_received += len(chunk)
                client_socket.sendall(f"MSG|Server successfully received {filename}.".encode('utf-8'))
                broadcast(f"MSG|[{addr[1]}] uploaded {filename}.".encode('utf-8'), client_socket)
                
            elif data.startswith("CMD|/download"):
                parts = data.split(' ')
                if len(parts) > 1:
                    filename = parts[1]
                    filepath = os.path.join(SERVER_DIR, filename)
                    
                    if os.path.exists(filepath):
                        filesize = os.path.getsize(filepath)
                        client_socket.sendall(f"FILE|{filename}|{filesize}".encode('utf-8'))
                        ready_msg = client_socket.recv(BUFFER_SIZE)
                        if ready_msg == b"READY":
                            with open(filepath, 'rb') as f:
                                while (chunk := f.read(BUFFER_SIZE)):
                                    client_socket.sendall(chunk)
                    else:
                        client_socket.sendall(f"MSG|Error: File '{filename}' not found.".encode('utf-8'))

    except Exception as e:
        print(f"[-] Error with client {addr}: {e}")
    finally:
        print(f"[-] Client {addr} disconnected.")
        if client_socket in clients:
            clients.remove(client_socket)
        client_socket.close()
        broadcast(f"MSG|Client [{addr[1]}] disconnected.".encode('utf-8'))

def start_thread_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    
    print(f"[THREAD SERVER] Listening on {HOST}:{PORT}")
    
    while True:
        # Acc client baru & bikin thread baru
        client_socket, addr = server_socket.accept()
        thread = threading.Thread(target=handle_client, args=(client_socket, addr))
        thread.start()

if __name__ == "__main__":
    start_thread_server()