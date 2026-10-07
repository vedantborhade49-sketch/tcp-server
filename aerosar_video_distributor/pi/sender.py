import socket
import sys
import os
import time
import cv2

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SERVER_HOST, SERVER_PORT, JPEG_QUALITY, FPS
from protocol import send_packet
from pi.camera_source import CameraSource

def run_sender():
    target_frame_time = 1.0 / FPS
    
    while True:
        cam = CameraSource(0)
        print("[PI] Attempting to initialize camera module...")
        if not cam.start():
            print("[PI] CAMERA: ERROR / UNAVAILABLE - Could not initialize real camera module")
            time.sleep(2)
            continue
            
        print("[PI] Camera initialized")
        
        frame_id = 0
        camera_active = True
        
        while camera_active:
            sock = None
            try:
                print(f"[PI] Connecting to {SERVER_HOST}:{SERVER_PORT}")
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((SERVER_HOST, SERVER_PORT))
                print("[PI] Connected to server")
                print("[PI] Sending frames...")
                
                consecutive_read_errors = 0
                frames_in_batch = 0
                bytes_in_batch = 0
                batch_start_time = time.time()
                
                while True:
                    loop_start = time.time()
                    
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
                    payload_size = len(jpeg_bytes)
                    
                    success = send_packet(sock, frame_id, timestamp, jpeg_bytes)
                    if not success:
                        print("[PI] Connection lost")
                        break
                        
                    # Stats tracking
                    frames_in_batch += 1
                    bytes_in_batch += payload_size
                    
                    if frame_id <= 2:
                        print(f"[PI] Frame {frame_id} | size={payload_size} bytes")
                        
                    current_time = time.time()
                    if current_time - batch_start_time >= 5.0:
                        elapsed = current_time - batch_start_time
                        current_fps = frames_in_batch / elapsed
                        mbps = (bytes_in_batch / 1024 / 1024) / elapsed
                        print(f"[PI] FPS: {current_fps:.1f} | TX: {mbps:.2f} MB/s | Frame ID: {frame_id}")
                        
                        frames_in_batch = 0
                        bytes_in_batch = 0
                        batch_start_time = current_time
                        
                    frame_id += 1
                    
                    # FPS regulation
                    elapsed_loop = time.time() - loop_start
                    sleep_time = target_frame_time - elapsed_loop
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                    
            except ConnectionRefusedError:
                print(f"[PI] Connection refused. Retrying in 2s...")
                time.sleep(2)
            except Exception as e:
                print(f"[PI] Connection error: {e}")
                time.sleep(2)
            finally:
                if sock:
                    try:
                        sock.close()
                    except:
                        pass
        
        # If we exit the camera_active loop, stop camera and start over
        print("[PI] Camera failure or clean shutdown, releasing resources...")
        cam.stop()
        time.sleep(2)

if __name__ == "__main__":
    run_sender()
