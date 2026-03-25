import socket
import os

HOST = '127.0.0.1'
PORT = 5000
BUFFER_SIZE = 4096

# Buat folder file server (klo blm ada)
SERVER_DIR = "server_files"
os.makedirs(SERVER_DIR, exist_ok=True)

def start_sync_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    
    print(f"[SYNC SERVER] Listening on {HOST}:{PORT}")
    print("Warning: This server handles ONE client at a time.")
    
    while True:
        # Block sampai ada client
        client_socket, addr = server_socket.accept() 
        print(f"[+] Client connected from {addr}")
        
        try:
            while True:
                data = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                if not data:
                    break # Client dc
                
                if data.startswith("CHAT|"):
                    msg = data[5:]
                    print(f"[{addr}] Chat: {msg}")
                    # Krn sync, hanya bc ke diri sendiri
                    client_socket.sendall(f"MSG|Broadcast: {msg}".encode('utf-8'))
                
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
                    
                elif data.startswith("CMD|/download"):
                    parts = data.split(' ')
                    if len(parts) > 1:
                        filename = parts[1]
                        filepath = os.path.join(SERVER_DIR, filename)
                        
                        if os.path.exists(filepath):
                            filesize = os.path.getsize(filepath)
                            # ada file dateng
                            client_socket.sendall(f"FILE|{filename}|{filesize}".encode('utf-8'))
                            
                            # Tunggu client ready
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
            print(f"[-] Client {addr} disconnected")
            client_socket.close()

if __name__ == "__main__":
    start_sync_server()