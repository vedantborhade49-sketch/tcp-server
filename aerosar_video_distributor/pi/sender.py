"""
AEROSAR - Raspberry Pi Video Sender

Captures camera frames -> encodes JPEG -> builds 16-byte header -> transmits over TCP to Laptop Server.
Supports configurable laptop IP and port.
"""
import sys
import os
import socket
import time
import argparse
from typing import Optional
import cv2

# Add parent directory to path to import protocol, config, and camera_source
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LAPTOP_IP, PI_PORT, JPEG_QUALITY, FRAME_WIDTH, FRAME_HEIGHT, FPS_TARGET
from protocol import send_packet
from pi.camera_source import CameraSource


def run_sender(
    host: str = LAPTOP_IP,
    port: int = PI_PORT,
    camera_type: str = "auto",
    camera_index: int = 0,
    width: int = FRAME_WIDTH,
    height: int = FRAME_HEIGHT,
    fps: int = FPS_TARGET,
    jpeg_quality: int = JPEG_QUALITY
) -> None:
    # 1. Initialize camera
    camera = CameraSource(
        camera_type=camera_type,
        width=width,
        height=height,
        fps=fps,
        camera_index=camera_index
    )

    if not camera.open():
        print("[PI] Error: Failed to open camera.")
        return

    print("[PI] Camera started")

    encode_params = [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality]
    frame_interval = 1.0 / max(1, fps)
    frame_id = 1
    sock: Optional[socket.socket] = None

    try:
        while True:
            # 2. Establish connection to laptop video server
            if sock is None:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    sock.connect((host, port))
                    print(f"[PI] Connected to server at {host}:{port}")
                except Exception:
                    if sock:
                        sock.close()
                        sock = None
                    time.sleep(1.0)
                    continue

            # 3. Capture and transmit loop
            try:
                while True:
                    loop_start = time.time()

                    ret, frame = camera.read()
                    if not ret or frame is None:
                        time.sleep(0.01)
                        continue

                    # Resize if dimensions differ
                    if frame.shape[1] != width or frame.shape[0] != height:
                        frame = cv2.resize(frame, (width, height))

                    # Encode to JPEG
                    ret, jpeg = cv2.imencode(".jpg", frame, encode_params)
                    if not ret:
                        continue

                    jpeg_bytes = jpeg.tobytes()
                    timestamp = int(time.time() * 1000)

                    # Build 16-byte header and send
                    send_packet(sock, frame_id, timestamp, jpeg_bytes)

                    if frame_id % 30 == 0:
                        print(f"[PI] Sent frame {frame_id}")

                    frame_id += 1

                    # FPS rate limiting / pacing
                    elapsed = time.time() - loop_start
                    sleep_time = frame_interval - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)

            except (ConnectionError, socket.error):
                print(f"[PI] Disconnected from server {host}:{port}. Reconnecting in 1s...")
                if sock:
                    try:
                        sock.close()
                    except Exception:
                        pass
                    sock = None
                time.sleep(1.0)

    except KeyboardInterrupt:
        print("\n[PI] Sender shutdown requested by user.")
    finally:
        if sock:
            try:
                sock.close()
            except Exception:
                pass
        camera.release()
        print("[PI] Camera released and sender stopped.")


def main():
    parser = argparse.ArgumentParser(description="AEROSAR Raspberry Pi Video Sender")
    parser.add_argument("--host", type=str, default=LAPTOP_IP, help=f"Laptop Server IP (default: {LAPTOP_IP})")
    parser.add_argument("--port", type=int, default=PI_PORT, help=f"Laptop Server Port (default: {PI_PORT})")
    parser.add_argument("--camera", type=str, default="auto", choices=["auto", "picam2", "opencv", "test"],
                        help="Camera source backend")
    parser.add_argument("--device", type=int, default=0, help="Camera index for OpenCV (default: 0)")
    parser.add_argument("--width", type=int, default=FRAME_WIDTH, help=f"Frame width (default: {FRAME_WIDTH})")
    parser.add_argument("--height", type=int, default=FRAME_HEIGHT, help=f"Frame height (default: {FRAME_HEIGHT})")
    parser.add_argument("--fps", type=int, default=FPS_TARGET, help=f"Target FPS (default: {FPS_TARGET})")
    parser.add_argument("--quality", type=int, default=JPEG_QUALITY, help=f"JPEG quality (default: {JPEG_QUALITY})")

    args = parser.parse_args()
    run_sender(
        host=args.host,
        port=args.port,
        camera_type=args.camera,
        camera_index=args.device,
        width=args.width,
        height=args.height,
        fps=args.fps,
        jpeg_quality=args.quality,
    )


if __name__ == "__main__":
    main()
