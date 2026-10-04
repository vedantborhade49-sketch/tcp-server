"""
AEROSAR - Test Webcam Sender (USB Webcam or Fallback)

Uses the 16-byte length-prefixed protocol to send webcam frames to Video Server on TCP 5000.
"""
import sys
import os
import socket
import time
import cv2

# Add parent directory to path to import protocol and config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LAPTOP_IP, PI_PORT, JPEG_QUALITY, FRAME_WIDTH, FRAME_HEIGHT, FPS_TARGET
from protocol import send_packet
from pi.camera_source import CameraSource


def run():
    print(f"[TEST SENDER] Initializing camera source for testing...")
    camera = CameraSource(camera_type="auto", width=FRAME_WIDTH, height=FRAME_HEIGHT, fps=FPS_TARGET)
    if not camera.open():
        print("[TEST SENDER] Failed to open any camera source.")
        return

    encode_params = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
    frame_interval = 1.0 / max(1, FPS_TARGET)
    frame_id = 1
    sock = None

    try:
        while True:
            if sock is None:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    sock.connect((LAPTOP_IP, PI_PORT))
                    print(f"[TEST SENDER] Connected to video server at {LAPTOP_IP}:{PI_PORT}")
                except Exception:
                    if sock:
                        sock.close()
                        sock = None
                    time.sleep(1.0)
                    continue

            try:
                while True:
                    loop_start = time.time()
                    ret, frame = camera.read()
                    if not ret or frame is None:
                        time.sleep(0.01)
                        continue

                    ret, jpeg = cv2.imencode(".jpg", frame, encode_params)
                    if not ret:
                        continue

                    jpeg_bytes = jpeg.tobytes()
                    timestamp = int(time.time() * 1000)

                    send_packet(sock, frame_id, timestamp, jpeg_bytes)

                    if frame_id % 30 == 0:
                        print(f"[TEST SENDER] Sent frame {frame_id}")

                    frame_id += 1

                    elapsed = time.time() - loop_start
                    sleep_time = frame_interval - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)

            except (ConnectionError, socket.error):
                print(f"[TEST SENDER] Disconnected. Reconnecting in 1s...")
                if sock:
                    try:
                        sock.close()
                    except Exception:
                        pass
                    sock = None
                time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[TEST SENDER] Stopped by user.")
    finally:
        if sock:
            try:
                sock.close()
            except Exception:
                pass
        camera.release()


if __name__ == "__main__":
    run()
