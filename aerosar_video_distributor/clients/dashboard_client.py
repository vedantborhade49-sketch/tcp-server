"""
AEROSAR - Dashboard Video Receiver (Client)

Connects to Laptop Video Server on TCP 6001.
Receives 16-byte header + JPEG bytes -> decodes OpenCV frame.
Does NOT perform YOLO, object detection, or UI redesign.
"""
import sys
import os
import socket
import time
from typing import Optional, Generator
import numpy as np
import cv2

# Add parent directory to path to import protocol and config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LAPTOP_IP, DASHBOARD_PORT
from protocol import read_header, read_exact


class DashboardReceiver:
    """Simple TCP client receiving frames from the central video server."""
    def __init__(self, host: str = LAPTOP_IP, port: int = DASHBOARD_PORT):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.running = False

    def connect(self) -> bool:
        """Attempts connection to the video server."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.sock.connect((self.host, self.port))
            print("[DASHBOARD] Connected")
            return True
        except Exception:
            if self.sock:
                self.sock.close()
                self.sock = None
            return False

    def frames(self) -> Generator[np.ndarray, None, None]:
        """Generator yielding decoded OpenCV BGR frames, reconnecting automatically."""
        self.running = True
        frame_counter = 0

        while self.running:
            if self.sock is None:
                if not self.connect():
                    time.sleep(1.0)
                    continue

            try:
                frame_id, timestamp, payload_size = read_header(self.sock)
                jpeg_bytes = read_exact(self.sock, payload_size)

                frame_data = np.frombuffer(jpeg_bytes, dtype=np.uint8)
                frame = cv2.imdecode(frame_data, cv2.IMREAD_COLOR)

                if frame is None:
                    continue

                frame_counter += 1
                if frame_counter % 30 == 0:
                    print(f"[DASHBOARD] Frame {frame_id} received")

                yield frame

            except (ConnectionError, socket.error):
                print("[DASHBOARD] Disconnected from server. Reconnecting in 1s...")
                if self.sock:
                    try:
                        self.sock.close()
                    except Exception:
                        pass
                    self.sock = None
                time.sleep(1.0)

    def close(self) -> None:
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None


def run(host: str = LAPTOP_IP, port: int = DASHBOARD_PORT) -> None:
    """Standalone preview runner for the Dashboard Receiver."""
    receiver = DashboardReceiver(host=host, port=port)
    try:
        for frame in receiver.frames():
            cv2.imshow("AEROSAR - Dashboard Receiver", frame)
            if cv2.waitKey(1) & 0xFF in [ord('q'), ord('Q')]:
                print("[DASHBOARD] Quit requested by user.")
                break
    except KeyboardInterrupt:
        print("\n[DASHBOARD] Stopped.")
    finally:
        receiver.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    target_host = sys.argv[1] if len(sys.argv) > 1 else LAPTOP_IP
    run(host=target_host)
