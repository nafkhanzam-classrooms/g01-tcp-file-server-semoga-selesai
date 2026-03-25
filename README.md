[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/mRmkZGKe)
# Network Programming - Assignment G01

## Anggota Kelompok
| Nama           | NRP        | Kelas     |
| ---            | ---        | ----------|
| Melvan Hapianan Allo Ponglabba                |  5025241124          |     Progjar - D      |


## Link Youtube (Unlisted)
Link ditaruh di bawah ini
```
https://youtu.be/weM4sptl9_o
```

## Penjelasan Program
### client.py
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
Client menggunakan pendekatan multithreading. Main thread digunakan untuk menangani input dari user (mengetik command/chat), sedangkan sebuah background thread berjalan secara bersamaan untuk terus mendengarkan broadcast message atau transfer file dari server. Hal ini memastikan aplikasi client tidak pernah freeze saat menunggu balasan server.


### server-sync.py
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
Ini adalah server baseline yang bersifat blocking / synchronous. Server ini hanya bisa menangani satu client pada satu waktu. Jika ada client kedua yang mencoba connect, mereka akan terjebak dalam antrian (waiting) sampai client pertama disconnect.

### server-select.py
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
Daripada membuat banyak thread, server ini hanya menggunakan satu thread utama dan memanfaatkan fungsi select.select() untuk secara cepat memonitor daftar seluruh socket yang terkoneksi. Server hanya akan memproses socket yang secara aktif siap untuk mengirim atau menerima data.

  ### server-thread.py
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
Server ini memecahkan masalah blocking dengan cara melakukan spawning / membuat sebuah background thread baru untuk setiap client yang terkoneksi. Hal ini memungkinkan banyak pengguna untuk chatting secara bersamaan.

  ### server-poll.py (Ubuntu/WSL only)
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
Ini adalah versi I/O multiplexing yang jauh lebih efisien dibandingkan select. Alih-alih melakukan scanning terhadap daftar koneksi yang panjang, poll() mendaftarkan socket langsung ke sistem operasi (OS kernel). OS akan langsung mengirimkan "event" ketika ada data yang masuk. Sistem pemanggilan poll() hanya didukung oleh arsitektur Unix (Linux/macOS) dan tidak dapat dijalankan secara native di Windows PowerShell tanpa WSL.
## Screenshot Hasil

### Server-sync
<img width="582" height="187" alt="image" src="https://github.com/user-attachments/assets/f00a5298-f9a8-4acc-af6f-bfedffd973cb" />

### Server-select
<img width="595" height="147" alt="image" src="https://github.com/user-attachments/assets/305788e6-a3d1-4a41-9413-7da16a5ef385" />

### Server-thread
<img width="619" height="181" alt="image" src="https://github.com/user-attachments/assets/ef88ec5b-7af7-4765-aa50-3761fc90cf73" />

### Server-poll
![Uploading image.png…]()

### Broadcast dari client lain



