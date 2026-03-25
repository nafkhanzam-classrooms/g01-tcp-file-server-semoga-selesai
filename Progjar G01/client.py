import socket
import threading
import os
import time

HOST = '127.0.0.1'
PORT = 5000
BUFFER_SIZE = 4096

def receive_messages(sock):
    """Listens for incoming broadcasts or file downloads from the server."""
    while True:
        try:
            # Awalan message ada tag "MSG|" or "FILE|"
            header = sock.recv(BUFFER_SIZE).decode('utf-8')
            if not header:
                print("\nDisconnected from server.")
                break
            
            if header.startswith("MSG|"):
                print(f"\n{header[4:]}")
            
            elif header.startswith("FILE|"):
                # Protocol: FILE|filename|filesize
                _, filename, filesize = header.split('|')
                filesize = int(filesize)
                print(f"\nDownloading {filename} ({filesize} bytes)...")
                
                # Siap nerima bytes
                sock.sendall(b"READY") 
                
                bytes_received = 0
                with open(f"client_downloads_{filename}", 'wb') as f:
                    while bytes_received < filesize:
                        chunk = sock.recv(min(BUFFER_SIZE, filesize - bytes_received))
                        if not chunk: break
                        f.write(chunk)
                        bytes_received += len(chunk)
                print(f"\nDownload of {filename} complete!")
                
        except Exception as e:
            print(f"\nError receiving: {e}")
            break

def start_client():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((HOST, PORT))
        print("Connected to server! Type a message or command (/list, /upload <file>, /download <file>).")
        
        # Background thread detect server messages
        receive_thread = threading.Thread(target=receive_messages, args=(client_socket,))
        receive_thread.daemon = True
        receive_thread.start()
        
        # Main thread user input
        while True:
            msg = input("")
            if msg.startswith("/upload"):
                parts = msg.split(" ", 1)
                if len(parts) < 2:
                    print("Usage: /upload <filename>")
                    continue
                filename = parts[1]
                if not os.path.exists(filename):
                    print("File does not exist on your computer.")
                    continue
                
                filesize = os.path.getsize(filename)
                client_socket.sendall(f"CMD|/upload|{filename}|{filesize}".encode('utf-8'))
                
                # tunggu server selesai proses header
                time.sleep(0.5) 
                with open(filename, 'rb') as f:
                    while (chunk := f.read(BUFFER_SIZE)):
                        client_socket.sendall(chunk)
                print("Upload sent.")
                
            elif msg.startswith("/list") or msg.startswith("/download"):
                client_socket.sendall(f"CMD|{msg}".encode('utf-8'))
            else:
                # Chat Broadcast 
                client_socket.sendall(f"CHAT|{msg}".encode('utf-8'))
                
    except ConnectionRefusedError:
        print("Could not connect to the server. Is it running?")
    finally:
        client_socket.close()

if __name__ == "__main__":
    start_client()