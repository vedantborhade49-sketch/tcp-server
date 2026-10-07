import socket
import threading
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import HOST, PI_PORT, DASHBOARD_PORT, ROS_PORT, STATUS_INTERVAL
from protocol import read_packet, send_raw_packet

class VideoServer:
    def __init__(self):
        self.latest_packet = None
        self.packet_lock = threading.Lock()
        
        self.pi_connected = False
        self.dashboard_connected = False
        self.ros_connected = False
        
        self.frames_received = 0
        self.bytes_received = 0
        self.frames_forwarded = 0
        self.bytes_forwarded = 0
        
        self.last_frames_received = 0
        self.last_time = time.time()
        
    def run(self):
        print(f"[SERVER] Listening on {HOST}:{PI_PORT}")
        print(f"[SERVER] Dashboard waiting on port {DASHBOARD_PORT}")
        print(f"[SERVER] ROS waiting on port {ROS_PORT}")
        
        threading.Thread(target=self.serve_client, args=(DASHBOARD_PORT, "Dashboard"), daemon=True).start()
        threading.Thread(target=self.serve_client, args=(ROS_PORT, "ROS"), daemon=True).start()
        threading.Thread(target=self.monitor_stats, daemon=True).start()
        
        self.listen_to_pi()

    def monitor_stats(self):
        while True:
            time.sleep(STATUS_INTERVAL)
            curr_time = time.time()
            dt = curr_time - self.last_time
            if dt == 0: dt = 1
            
            fps = (self.frames_received - self.last_frames_received) / dt
            self.last_frames_received = self.frames_received
            self.last_time = curr_time
            
            with self.packet_lock:
                pkt = self.latest_packet
                fid = pkt[0] if pkt else -1
                ts = pkt[1] if pkt else 0
                
            pi_status = "UP" if self.pi_connected else "DOWN"
            dash_status = "UP" if self.dashboard_connected else "DOWN"
            ros_status = "UP" if self.ros_connected else "DOWN"
            
            print(f"--- STATS ---")
            print(f"PI: {pi_status} | DASH: {dash_status} | ROS: {ros_status}")
            print(f"FPS: {fps:.1f} | Frame: {fid} | Timestamp: {ts}")
            print(f"RX: {self.frames_received} frames ({self.bytes_received / 1024 / 1024:.2f} MB)")
            print(f"TX: {self.frames_forwarded} frames ({self.bytes_forwarded / 1024 / 1024:.2f} MB)")
            print(f"-------------")

    def listen_to_pi(self):
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((HOST, PI_PORT))
        server_sock.listen(1)
        
        while True:
            try:
                conn, addr = server_sock.accept()
                self.pi_connected = True
                print(f"[SERVER] Raspberry Pi connected: {addr}")
                self.handle_pi(conn)
            except Exception as e:
                time.sleep(1)

    def handle_pi(self, conn: socket.socket):
        try:
            while True:
                packet_data = read_packet(conn)
                if not packet_data:
                    break
                    
                frame_id, timestamp, jpeg_bytes, raw_packet = packet_data
                self.frames_received += 1
                self.bytes_received += len(raw_packet)
                
                with self.packet_lock:
                    self.latest_packet = packet_data
        except Exception:
            pass
        finally:
            with self.packet_lock:
                self.latest_packet = None
            self.pi_connected = False
            print("[SERVER] Raspberry Pi disconnected")
            conn.close()

    def serve_client(self, port: int, client_name: str):
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((HOST, port))
        server_sock.listen(1)
        
        while True:
            try:
                conn, addr = server_sock.accept()
                if client_name == "Dashboard":
                    self.dashboard_connected = True
                elif client_name == "ROS":
                    self.ros_connected = True
                    
                print(f"[SERVER] {client_name} connected: {addr}")
                self.handle_client(conn, client_name)
                
                if client_name == "Dashboard":
                    self.dashboard_connected = False
                elif client_name == "ROS":
                    self.ros_connected = False
                    
                print(f"[SERVER] {client_name} disconnected")
            except Exception:
                time.sleep(1)

    def handle_client(self, conn: socket.socket, client_name: str):
        import select
        last_sent_frame_id = -1
        try:
            while True:
                # Check for client disconnect
                readable, _, _ = select.select([conn], [], [], 0.0)
                if readable:
                    try:
                        data = conn.recv(1024)
                        if not data:
                            break
                    except (ConnectionResetError, ConnectionAbortedError, ConnectionError, BrokenPipeError):
                        break
                
                packet = None
                with self.packet_lock:
                    if self.latest_packet and self.latest_packet[0] > last_sent_frame_id:
                        packet = self.latest_packet
                        last_sent_frame_id = packet[0]
                
                if packet:
                    frame_id, timestamp, jpeg_bytes, raw_packet = packet
                    success = send_raw_packet(conn, raw_packet)
                    if not success:
                        break
                        
                    self.frames_forwarded += 1
                    self.bytes_forwarded += len(raw_packet)
                else:
                    time.sleep(0.01) # Avoid tight polling
        except Exception:
            pass
        finally:
            conn.close()

if __name__ == "__main__":
    VideoServer().run()
