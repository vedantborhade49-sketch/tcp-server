"""
AEROSAR - Central Video Server (Laptop)

Architecture:
  Pi Camera  --> TCP 5000 --> Video Server
                                  |
                   +--------------+--------------+
                   |                             |
             TCP 6001 (Dashboard)          TCP 6002 (ROS)

- Accepts Pi camera connection on 0.0.0.0:5000.
- Decodes JPEG to keep the latest frame.
- Forwards original raw JPEG packet to connected Dashboard (6001) and ROS (6002).
- Zero re-encoding overhead.
"""
import sys
import os
import socket
import threading
import time
from typing import Optional
import numpy as np
import cv2

# Add parent directory to path to import protocol and config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SERVER_HOST, PI_PORT, DASHBOARD_PORT, ROS_PORT
from protocol import read_header, read_exact, create_packet


class VideoServer:
    def __init__(
        self,
        host: str = SERVER_HOST,
        pi_port: int = PI_PORT,
        dashboard_port: int = DASHBOARD_PORT,
        ros_port: int = ROS_PORT,
    ):
        self.host = host
        self.pi_port = pi_port
        self.dashboard_port = dashboard_port
        self.ros_port = ros_port

        self.running = False
        self.lock = threading.Lock()

        self.dashboard_socket: Optional[socket.socket] = None
        self.ros_socket: Optional[socket.socket] = None

        # Latest decoded frame buffer
        self.latest_frame: Optional[np.ndarray] = None
        self.latest_frame_id: int = 0
        self.latest_timestamp: int = 0

    def _dashboard_listener(self) -> None:
        """Background thread listening for Dashboard receiver on DASHBOARD_PORT."""
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            srv.bind((self.host, self.dashboard_port))
            srv.listen(1)
        except Exception as e:
            print(f"[SERVER] Failed to bind Dashboard port {self.dashboard_port}: {e}")
            srv.close()
            return

        while self.running:
            try:
                client_sock, _ = srv.accept()
                client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                client_sock.settimeout(0.5)  # Avoid blocking if client stalls
                with self.lock:
                    if self.dashboard_socket is not None:
                        try:
                            self.dashboard_socket.close()
                        except Exception:
                            pass
                    self.dashboard_socket = client_sock
                print("[SERVER] Dashboard connected")
            except Exception:
                if not self.running:
                    break
        srv.close()

    def _ros_listener(self) -> None:
        """Background thread listening for ROS receiver on ROS_PORT."""
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            srv.bind((self.host, self.ros_port))
            srv.listen(1)
        except Exception as e:
            print(f"[SERVER] Failed to bind ROS port {self.ros_port}: {e}")
            srv.close()
            return

        while self.running:
            try:
                client_sock, _ = srv.accept()
                client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                client_sock.settimeout(0.5)  # Avoid blocking if client stalls
                with self.lock:
                    if self.ros_socket is not None:
                        try:
                            self.ros_socket.close()
                        except Exception:
                            pass
                    self.ros_socket = client_sock
                print("[SERVER] ROS connected")
            except Exception:
                if not self.running:
                    break
        srv.close()

    def start(self) -> None:
        """Starts the server and handles incoming frames from Raspberry Pi."""
        self.running = True

        # Start distribution listener threads
        t_dash = threading.Thread(target=self._dashboard_listener, daemon=True)
        t_ros = threading.Thread(target=self._ros_listener, daemon=True)
        t_dash.start()
        t_ros.start()

        pi_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        pi_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        pi_server.bind((self.host, self.pi_port))
        pi_server.listen(1)

        print(f"[SERVER] Listening on {self.host}:{self.pi_port}")

        try:
            while self.running:
                try:
                    pi_sock, _ = pi_server.accept()
                    pi_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    print("[SERVER] Pi connected")
                except Exception:
                    if not self.running:
                        break
                    continue

                frame_counter = 0

                try:
                    while self.running:
                        # 1. Read 16-byte header
                        frame_id, timestamp, payload_size = read_header(pi_sock)

                        # 2. Read exact JPEG bytes
                        jpeg_bytes = read_exact(pi_sock, payload_size)

                        # 3. Assemble full raw packet to forward
                        raw_packet = create_packet(frame_id, timestamp, jpeg_bytes)

                        # 4. Decode JPEG for local latest_frame storage
                        frame_data = np.frombuffer(jpeg_bytes, dtype=np.uint8)
                        decoded = cv2.imdecode(frame_data, cv2.IMREAD_COLOR)
                        if decoded is not None:
                            self.latest_frame = decoded
                            self.latest_frame_id = frame_id
                            self.latest_timestamp = timestamp

                        frame_counter += 1
                        sent_to_dash = False
                        sent_to_ros = False

                        # 5. Forward raw packet to Dashboard if connected
                        with self.lock:
                            dash_sock = self.dashboard_socket
                        if dash_sock is not None:
                            try:
                                dash_sock.sendall(raw_packet)
                                sent_to_dash = True
                            except Exception:
                                with self.lock:
                                    if self.dashboard_socket == dash_sock:
                                        self.dashboard_socket = None
                                try:
                                    dash_sock.close()
                                except Exception:
                                    pass
                                print("[SERVER] Dashboard disconnected")

                        # 6. Forward raw packet to ROS if connected
                        with self.lock:
                            r_sock = self.ros_socket
                        if r_sock is not None:
                            try:
                                r_sock.sendall(raw_packet)
                                sent_to_ros = True
                            except Exception:
                                with self.lock:
                                    if self.ros_socket == r_sock:
                                        self.ros_socket = None
                                try:
                                    r_sock.close()
                                except Exception:
                                    pass
                                print("[SERVER] ROS disconnected")

                        # 7. Print debug status periodically (every 30 frames)
                        if frame_counter % 30 == 0:
                            print(f"[SERVER] Frame {frame_id} received")
                            if sent_to_dash:
                                print(f"[SERVER] Frame {frame_id} \u2192 dashboard")
                            if sent_to_ros:
                                print(f"[SERVER] Frame {frame_id} \u2192 ROS")

                except (ConnectionError, socket.error) as e:
                    print(f"[SERVER] Pi disconnected ({e}). Waiting for reconnection...")
                finally:
                    try:
                        pi_sock.close()
                    except Exception:
                        pass
        except KeyboardInterrupt:
            print("\n[SERVER] Shutdown requested by user.")
        finally:
            self.stop()
            pi_server.close()
            print("[SERVER] Stopped.")

    def stop(self) -> None:
        self.running = False
        with self.lock:
            if self.dashboard_socket:
                try:
                    self.dashboard_socket.close()
                except Exception:
                    pass
                self.dashboard_socket = None
            if self.ros_socket:
                try:
                    self.ros_socket.close()
                except Exception:
                    pass
                self.ros_socket = None


if __name__ == "__main__":
    server = VideoServer()
    server.start()
