import socket
import sys
import os
import cv2
import numpy as np
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LAPTOP_IP, DASHBOARD_PORT
from protocol import read_packet

def run_dashboard_client():
    while True:
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((LAPTOP_IP, DASHBOARD_PORT))
            print("[DASHBOARD] Connected")
            
            frames_received = 0
            while True:
                packet_data = read_packet(sock)
                if not packet_data:
                    break
                    
                frame_id, timestamp, jpeg_bytes = packet_data
                frames_received += 1
                
                if frames_received % 30 == 0:
                    print(f"[DASHBOARD] Frame {frame_id} received")
                    
                # Decode frame for existing integration
                frame = cv2.imdecode(np.frombuffer(jpeg_bytes, np.uint8), cv2.IMREAD_COLOR)
                
                # ----- EXISTING DASHBOARD INTEGRATION GOES HERE -----
                # Pass 'frame' to the dashboard
                # For testing:
                # cv2.imshow("Dashboard View", frame)
                # if cv2.waitKey(1) & 0xFF == ord('q'): break
                
        except ConnectionRefusedError:
            time.sleep(2)
        except Exception:
            time.sleep(2)
        finally:
            if sock is not None:
                try:
                    sock.close()
                except:
                    pass
            # cv2.destroyAllWindows()

if __name__ == "__main__":
    run_dashboard_client()
