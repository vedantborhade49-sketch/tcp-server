"""
AEROSAR - Fake Video Sender for Laptop Testing

Generates synthetic video frames and transmits them to Video Server on TCP 5000.
Allows testing the entire pipeline on a laptop without physical camera hardware.
"""
import sys
import os
import socket
import time
import argparse
from typing import Optional
import numpy as np
import cv2

# Add parent directory to path to import protocol and config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LAPTOP_IP, PI_PORT, JPEG_QUALITY, FRAME_WIDTH, FRAME_HEIGHT, FPS_TARGET
from protocol import send_packet


def run_fake_sender(
    host: str = LAPTOP_IP,
    port: int = PI_PORT,
    width: int = FRAME_WIDTH,
    height: int = FRAME_HEIGHT,
    fps: int = FPS_TARGET,
    jpeg_quality: int = JPEG_QUALITY
) -> None:
    print(f"[FAKE SENDER] Starting synthetic video generator ({width}x{height} @ {fps} FPS)...")
    print(f"[FAKE SENDER] Target destination: {host}:{port}")

    encode_params = [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality]
    frame_interval = 1.0 / max(1, fps)
    frame_id = 1
    sock: Optional[socket.socket] = None

    try:
        while True:
            # 1. Connect
            if sock is None:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    sock.connect((host, port))
                    print(f"[FAKE SENDER] Connected to server at {host}:{port}")
                except Exception:
                    if sock:
                        sock.close()
                        sock = None
                    time.sleep(1.0)
                    continue

            # 2. Generate and stream
            try:
                while True:
                    loop_start = time.time()

                    # Generate synthetic frame
                    frame = np.zeros((height, width, 3), dtype=np.uint8)
                    frame[:] = (30, 30, 30)

                    # Dynamic animated element
                    box_x = int((frame_id * 10) % (width - 120))
                    box_y = int(height / 2 - 60)
                    cv2.rectangle(frame, (box_x, box_y), (box_x + 120, box_y + 120), (0, 200, 255), -1)

                    cv2.putText(
                        frame, "AEROSAR FAKE SENDER (TEST 1)",
                        (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2
                    )
                    cv2.putText(
                        frame, f"Frame ID: {frame_id} | Time: {time.strftime('%H:%M:%S')}",
                        (30, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2
                    )

                    # Encode to JPEG
                    ret, jpeg = cv2.imencode(".jpg", frame, encode_params)
                    if not ret:
                        continue

                    jpeg_bytes = jpeg.tobytes()
                    timestamp = int(time.time() * 1000)

                    # Send packet
                    send_packet(sock, frame_id, timestamp, jpeg_bytes)

                    if frame_id % 30 == 0:
                        print(f"[FAKE SENDER] Sent frame {frame_id}")

                    frame_id += 1

                    # Pacing
                    elapsed = time.time() - loop_start
                    sleep_time = frame_interval - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)

            except (ConnectionError, socket.error):
                print(f"[FAKE SENDER] Disconnected from server {host}:{port}. Reconnecting in 1s...")
                if sock:
                    try:
                        sock.close()
                    except Exception:
                        pass
                    sock = None
                time.sleep(1.0)

    except KeyboardInterrupt:
        print("\n[FAKE SENDER] Stopped by user.")
    finally:
        if sock:
            try:
                sock.close()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="AEROSAR Fake Sender")
    parser.add_argument("--host", type=str, default=LAPTOP_IP, help=f"Server IP (default: {LAPTOP_IP})")
    parser.add_argument("--port", type=int, default=PI_PORT, help=f"Server Port (default: {PI_PORT})")
    parser.add_argument("--fps", type=int, default=FPS_TARGET, help=f"FPS (default: {FPS_TARGET})")
    parser.add_argument("--width", type=int, default=FRAME_WIDTH, help=f"Width (default: {FRAME_WIDTH})")
    parser.add_argument("--height", type=int, default=FRAME_HEIGHT, help=f"Height (default: {FRAME_HEIGHT})")

    args = parser.parse_args()
    run_fake_sender(
        host=args.host,
        port=args.port,
        width=args.width,
        height=args.height,
        fps=args.fps
    )


if __name__ == "__main__":
    main()
