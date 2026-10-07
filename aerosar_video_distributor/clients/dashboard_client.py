import socket
import sys
import os
import cv2
import numpy as np
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LAPTOP_IP, DASHBOARD_PORT, FRAME_TIMEOUT
from protocol import read_packet

def run_dashboard_client():
    cv2.namedWindow("Dashboard View", cv2.WINDOW_NORMAL)
    
    while True:
        sock = None
        state = "CONNECTING"
        
        # Show connecting state
        blank_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        cv2.putText(blank_frame, "STATUS: CONNECTING...", (400, 360), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)
        cv2.imshow("Dashboard View", blank_frame)
        cv2.waitKey(1)
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((LAPTOP_IP, DASHBOARD_PORT))
            sock.settimeout(0.5)
            
            frames_received = 0
            last_frame_time = time.time()
            camera_online = False
            state = "OFFLINE"
            
            while True:
                try:
                    packet_data = read_packet(sock)
                    if not packet_data:
                        break
                except (socket.timeout, TimeoutError):
                    packet_data = None
                    
                current_time = time.time()
                
                if packet_data:
                    frame_id, timestamp, jpeg_bytes, raw_packet = packet_data
                    frames_received += 1
                    last_frame_time = current_time
                    camera_online = True
                    state = "LIVE"
                    
                    if frames_received % 30 == 0:
                        print(f"[DASHBOARD] Frame {frame_id} received")
                        
                    # Decode frame for existing integration
                    frame = cv2.imdecode(np.frombuffer(jpeg_bytes, np.uint8), cv2.IMREAD_COLOR)
                    
                    if frame is not None:
                        # ----- EXISTING DASHBOARD INTEGRATION GOES HERE -----
                        # YOLO only runs here on valid live frames
                        
                        # Optionally draw a small LIVE indicator
                        cv2.circle(frame, (30, 30), 10, (0, 255, 0), -1)
                        cv2.putText(frame, "LIVE", (50, 38), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                        
                        cv2.imshow("Dashboard View", frame)
                    
                    if cv2.waitKey(1) & 0xFF == ord('q'): break
                else:
                    if current_time - last_frame_time > FRAME_TIMEOUT:
                        if camera_online:
                            print("[DASHBOARD] CAMERA OFFLINE")
                        camera_online = False
                        state = "OFFLINE"
                        
                        # Show offline state
                        blank_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
                        cv2.putText(blank_frame, "STATUS: OFFLINE / ERROR", (320, 360), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
                        cv2.putText(blank_frame, "Waiting for valid camera frames from Raspberry Pi", (250, 420), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                        
                        cv2.imshow("Dashboard View", blank_frame)
                        if cv2.waitKey(1) & 0xFF == ord('q'): break
                
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
