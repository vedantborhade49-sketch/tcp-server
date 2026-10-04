"""
Test client for Dashboard
"""
import sys
import os
import socket
import time
import cv2
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DASHBOARD_HOST, DASHBOARD_PORT
from distributor.protocol import HEADER_SIZE, unpack_header

def receive_exact(sock, size):
    data = bytearray()
    while len(data) < size:
        packet = sock.recv(size - len(data))
        if not packet:
            raise ConnectionError("Connection closed")
        data.extend(packet)
    return bytes(data)

def run():
    print(f"[DASHBOARD] Starting TCP Receiver connecting to {DASHBOARD_HOST}:{DASHBOARD_PORT}...")
    
    while True:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((DASHBOARD_HOST, DASHBOARD_PORT))
            print(f"[DASHBOARD] Connected to {DASHBOARD_HOST}:{DASHBOARD_PORT}")
        except Exception as e:
            print(f"[DASHBOARD] Waiting for distributor at {DASHBOARD_HOST}:{DASHBOARD_PORT}... ({e})")
            time.sleep(1.0)
            continue

        frames_received = 0
        start_time = time.time()
        
        try:
            while True:
                header_bytes = receive_exact(sock, HEADER_SIZE)
                frame_id, timestamp_ns, payload_size, width, height = unpack_header(header_bytes)
                
                payload_bytes = receive_exact(sock, payload_size)
                frame_data = np.frombuffer(payload_bytes, dtype=np.uint8)
                frame = cv2.imdecode(frame_data, cv2.IMREAD_COLOR)
                
                if frame is None:
                    continue
                    
                frames_received += 1
                elapsed = time.time() - start_time
                fps = frames_received / elapsed if elapsed > 0 else 0
                
                print(f"[DASHBOARD] Frame ID={frame_id} | {width}x{height} | {fps:.1f} FPS")
                
                cv2.putText(frame, f"Frame ID: {frame_id}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                cv2.putText(frame, f"FPS: {fps:.1f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                
                cv2.imshow("AEROSAR - Dashboard Receiver", frame)
                if cv2.waitKey(1) & 0xFF in [ord('q'), ord('Q')]:
                    print("[DASHBOARD] Shutdown requested by user.")
                    return
        except Exception as e:
            print(f"[DASHBOARD] Disconnected: {e}. Reconnecting in 1s...")
            time.sleep(1.0)
        finally:
            try:
                sock.close()
            except Exception:
                pass
            cv2.destroyAllWindows()

if __name__ == "__main__":
    run()
