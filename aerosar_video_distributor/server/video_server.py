import socket
import threading
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SERVER_HOST, PI_PORT, DASHBOARD_PORT, ROS_PORT
from protocol import read_packet

class VideoServer:
    def __init__(self):
        self.latest_packet = None
        self.packet_lock = threading.Lock()
        
    def run(self):
        print(f"[SERVER] Listening on {SERVER_HOST}:{PI_PORT}")
        print(f"[SERVER] Waiting for Raspberry Pi/video sender...")
        print(f"[SERVER] Dashboard waiting on port {DASHBOARD_PORT}")
        print(f"[SERVER] ROS waiting on port {ROS_PORT}")
        
        # Start Dashboard and ROS servers
        threading.Thread(target=self.serve_client, args=(DASHBOARD_PORT, "Dashboard"), daemon=True).start()
        threading.Thread(target=self.serve_client, args=(ROS_PORT, "ROS"), daemon=True).start()
        
        # Main thread handles Pi connection
        self.listen_to_pi()

    def listen_to_pi(self):
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((SERVER_HOST, PI_PORT))
        server_sock.listen(1)
        
        while True:
            try:
                conn, addr = server_sock.accept()
                print(f"[SERVER] Raspberry Pi/video sender connected")
                self.handle_pi(conn)
            except Exception as e:
                time.sleep(1)

    def handle_pi(self, conn: socket.socket):
        frames_received = 0
        try:
            while True:
                packet_data = read_packet(conn)
                if not packet_data:
                    break
                    
                frame_id, timestamp, jpeg_bytes = packet_data
                frames_received += 1
                
                if frames_received % 30 == 0:
                    print(f"[SERVER] Frame {frame_id} received")
                
                with self.packet_lock:
                    self.latest_packet = (frame_id, timestamp, jpeg_bytes)
        except Exception:
            pass
        finally:
            with self.packet_lock:
                self.latest_packet = None
            print("[SERVER] Raspberry Pi/video sender disconnected")
            print(f"[SERVER] Waiting for Raspberry Pi/video sender...")
            conn.close()

    def serve_client(self, port: int, client_name: str):
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((SERVER_HOST, port))
        server_sock.listen(1)
        
        while True:
            try:
                conn, addr = server_sock.accept()
                print(f"[SERVER] {client_name} connected")
                self.handle_client(conn, client_name)
                print(f"[SERVER] {client_name} disconnected")
                print(f"[SERVER] {client_name} waiting on port {port}")
            except Exception:
                time.sleep(1)

    def handle_client(self, conn: socket.socket, client_name: str):
        import protocol
        import select
        last_sent_frame_id = -1
        frames_sent = 0
        try:
            while True:
                # Check if client has disconnected (socket becomes readable on close)
                readable, _, _ = select.select([conn], [], [], 0.0)
                if readable:
                    try:
                        data = conn.recv(1024)
                        if not data:
                            break  # Clean disconnect
                    except (ConnectionResetError, ConnectionAbortedError, ConnectionError, BrokenPipeError):
                        break  # Forceful disconnect
                
                packet = None
                with self.packet_lock:
                    if self.latest_packet and self.latest_packet[0] > last_sent_frame_id:
                        packet = self.latest_packet
                        last_sent_frame_id = packet[0]
                
                if packet:
                    frame_id, timestamp, jpeg_bytes = packet
                    success = protocol.send_packet(conn, frame_id, timestamp, jpeg_bytes)
                    if not success:
                        break
                        
                    frames_sent += 1
                    if frames_sent % 30 == 0:
                        print(f"[SERVER] Frame {frame_id} → {client_name}")
                else:
                    time.sleep(0.01) # Prevent tight loop
        except Exception:
            pass
        finally:
            conn.close()

if __name__ == "__main__":
    VideoServer().run()
