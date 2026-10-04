import socket
import sys
import os
import time
import cv2
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LAPTOP_IP, PI_PORT, JPEG_QUALITY, FRAME_WIDTH, FRAME_HEIGHT
from protocol import send_packet

def generate_test_frame(frame_id):
    frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
    cv2.putText(frame, f"FAKE FRAME: {frame_id}", (50, 100), 
                cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 255, 0), 5)
    return frame

def run_fake_sender():
    print("[PI] Camera started")
    frame_id = 0
    
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((LAPTOP_IP, PI_PORT))
            print("[PI] Connected to server")
            
            while True:
                frame = generate_test_frame(frame_id)
                timestamp = int(time.time() * 1000)
                
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
                _, jpeg_encoded = cv2.imencode('.jpg', frame, encode_param)
                jpeg_bytes = jpeg_encoded.tobytes()
                
                success = send_packet(sock, frame_id, timestamp, jpeg_bytes)
                if not success:
                    break
                    
                if frame_id % 30 == 0:
                    print(f"[PI] Sent frame {frame_id}")
                    
                frame_id += 1
                time.sleep(0.033)  # Approx 30 FPS
                
        except ConnectionRefusedError:
            time.sleep(2)
        except Exception:
            time.sleep(2)
        finally:
            try:
                sock.close()
            except:
                pass

if __name__ == "__main__":
    run_fake_sender()
