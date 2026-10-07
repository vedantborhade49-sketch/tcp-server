import socket
import sys
import os
import time
import cv2

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SERVER_HOST, SERVER_PORT, JPEG_QUALITY, FPS, CAMERA_INDEX, FRAME_WIDTH, FRAME_HEIGHT
from protocol import send_packet
from pi.camera_source import CameraSource

def run_sender():
    target_frame_time = 1.0 / FPS
    
    print("[PI] AEROSAR Raspberry Pi Camera Sender")
    print("[PI] Camera: USB")
    print(f"[PI] Camera index: {CAMERA_INDEX}")
    print(f"[PI] Resolution: {FRAME_WIDTH}x{FRAME_HEIGHT}")
    print(f"[PI] Target FPS: {FPS}")
    print(f"[PI] JPEG quality: {JPEG_QUALITY}")
    print(f"[PI] Server: {SERVER_HOST}:{SERVER_PORT}")
    
    cam = CameraSource(CAMERA_INDEX)
    if not cam.start():
        print("[PI] ERROR: Unable to open USB camera")
        sys.exit(1)
        
    frame_id = 0
    sock = None
    
    try:
        while True:
            try:
                print("[PI] Connecting to server...")
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((SERVER_HOST, SERVER_PORT))
                print("[PI] Connected to laptop video server")
                
                frames_in_batch = 0
                batch_start_time = time.time()
                
                while True:
                    loop_start = time.time()
                    
                    ret, frame = cam.read()
                    if not ret or frame is None:
                        print("[PI] ERROR: Unable to capture frame from USB camera. Camera disconnected?")
                        sys.exit(1)
                        
                    timestamp = int(time.time() * 1000)
                    
                    # Encode JPEG
                    encode_param = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
                    _, jpeg_encoded = cv2.imencode('.jpg', frame, encode_param)
                    jpeg_bytes = jpeg_encoded.tobytes()
                    
                    success = send_packet(sock, frame_id, timestamp, jpeg_bytes)
                    if not success:
                        print("[PI] Connection lost")
                        print("[PI] Reconnecting in 2 seconds...")
                        break
                        
                    frames_in_batch += 1
                    frame_id += 1
                        
                    current_time = time.time()
                    if current_time - batch_start_time >= 5.0:
                        elapsed = current_time - batch_start_time
                        current_fps = frames_in_batch / elapsed
                        print(f"[PI] Frames sent: {frame_id} | FPS: {current_fps:.1f}")
                        
                        frames_in_batch = 0
                        batch_start_time = current_time
                        
                    # FPS regulation
                    elapsed_loop = time.time() - loop_start
                    sleep_time = target_frame_time - elapsed_loop
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                    
            except ConnectionRefusedError:
                print("[PI] Connection refused")
                print("[PI] Reconnecting in 2 seconds...")
                time.sleep(2)
            except Exception as e:
                print(f"[PI] Connection lost")
                print("[PI] Reconnecting in 2 seconds...")
                time.sleep(2)
            finally:
                if sock:
                    try:
                        sock.close()
                    except:
                        pass
                time.sleep(2) # Throttle reconnection attempts
                
    except KeyboardInterrupt:
        print("\n[PI] Shutting down...")
    finally:
        cam.stop()
        print("[PI] Camera released")
        if sock:
            try:
                sock.close()
            except:
                pass
        print("[PI] Socket closed")

if __name__ == "__main__":
    run_sender()
