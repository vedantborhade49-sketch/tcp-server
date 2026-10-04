import socket
import sys
import os
import time
import cv2

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LAPTOP_IP, PI_PORT, JPEG_QUALITY
from protocol import send_packet
from pi.camera_source import CameraSource

def run_sender():
    while True:
        cam = CameraSource(0)
        print("[PI] Attempting to initialize camera module...")
        if not cam.open():
            print("[PI] CAMERA: ERROR / UNAVAILABLE - Could not initialize real camera module")
            time.sleep(2)
            continue
            
        print("[PI] Camera started successfully")
        
        frame_id = 0
        camera_active = True
        
        while camera_active:
            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((LAPTOP_IP, PI_PORT))
                print("[PI] Connected to server")
                
                consecutive_read_errors = 0
                
                while True:
                    ret, frame = cam.read()
                    if not ret or frame is None:
                        consecutive_read_errors += 1
                        if consecutive_read_errors > 10:
                            print("[PI] CAMERA: ERROR / UNAVAILABLE - Repeatedly failed to read frame")
                            camera_active = False
                            break
                        time.sleep(0.1)
                        continue
                        
                    consecutive_read_errors = 0
                    timestamp = int(time.time() * 1000)
                    
                    # Encode JPEG
                    encode_param = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
                    _, jpeg_encoded = cv2.imencode('.jpg', frame, encode_param)
                    jpeg_bytes = jpeg_encoded.tobytes()
                    
                    success = send_packet(sock, frame_id, timestamp, jpeg_bytes)
                    if not success:
                        break
                        
                    if frame_id % 30 == 0:
                        print(f"[PI] Sent frame {frame_id}")
                        
                    frame_id += 1
                    
            except ConnectionRefusedError:
                time.sleep(2)
            except Exception:
                time.sleep(2)
            finally:
                if sock:
                    try:
                        sock.close()
                    except:
                        pass
        
        # If we exit the camera_active loop, release camera and start over
        cam.release()
        time.sleep(2)

if __name__ == "__main__":
    run_sender()
