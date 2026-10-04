"""
TCP server receiving video frames from the sender.
Decode the incoming packet structure.
Pass received frames to the distribution layer.
Must NOT contain YOLO, SLAM, RAG, LLM, or dashboard UI.
"""
import sys
import os
import socket
import time
import cv2
import numpy as np

import threading

# Add the project root to sys.path so we can import config and distributor modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import VIDEO_HOST, VIDEO_PORT, DASHBOARD_HOST, DASHBOARD_PORT, ROS_HOST, ROS_PORT
from distributor.protocol import HEADER_SIZE, unpack_header
from distributor.buffer import VideoBuffer

class VideoDistributorServer:
    def __init__(self):
        self.host = VIDEO_HOST
        self.port = VIDEO_PORT
        self.server_socket = None
        self.dashboard_socket = None
        self.ros_socket = None
        self.running = False
        self.buffer = VideoBuffer()

    def receive_exact(self, sock, size):
        """Helper to receive exactly 'size' bytes from the socket."""
        data = bytearray()
        while len(data) < size:
            packet = sock.recv(size - len(data))
            if not packet:
                raise ConnectionError("Connection closed before all bytes received")
            data.extend(packet)
        return bytes(data)

    def handle_client(self, client_sock):
        """Handles a connected sender client."""
        prev_frame_id = -1
        frames_received = 0
        start_time = time.time()
        
        try:
            while self.running:
                # 1. Receive Header
                try:
                    header_bytes = self.receive_exact(client_sock, HEADER_SIZE)
                except ConnectionError:
                    print("[CLIENT] Disconnected")
                    break
                
                frame_id, timestamp_ns, payload_size, width, height = unpack_header(header_bytes)
                
                # 2. Check Frame ID Ordering
                if prev_frame_id != -1 and frame_id <= prev_frame_id:
                    print(f"[WARNING] Unexpected frame ID: {frame_id} after {prev_frame_id}")
                prev_frame_id = frame_id
                
                # 3. Receive JPEG Payload
                try:
                    payload_bytes = self.receive_exact(client_sock, payload_size)
                except ConnectionError:
                    print("[CLIENT] Disconnected during payload")
                    break
                    
                # 4. Decode JPEG to OpenCV Frame
                frame_data = np.frombuffer(payload_bytes, dtype=np.uint8)
                frame = cv2.imdecode(frame_data, cv2.IMREAD_COLOR)
                
                if frame is None:
                    print(f"[ERROR] Failed to decode frame {frame_id}. Discarding.")
                    continue
                    
                # 4.5 Push to buffer for output clients
                self.buffer.push(header_bytes, payload_bytes)
                    
                # 5. Measure Latency and FPS
                latency_ms = (time.time_ns() - timestamp_ns) / 1_000_000.0
                
                frames_received += 1
                elapsed = time.time() - start_time
                rx_fps = frames_received / elapsed if elapsed > 0 else 0
                
                # 6. Logging
                print(f"[FRAME] ID={frame_id} | {width}x{height} | {rx_fps:.1f} FPS | {latency_ms:.1f} ms")
                
                # 7. Display Frame
                cv2.putText(frame, f"Frame ID: {frame_id}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, f"RX FPS: {rx_fps:.1f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, f"Latency: {latency_ms:.1f} ms", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, f"Res: {width}x{height}", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, f"Timestamp: {timestamp_ns}", (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                cv2.imshow("AEROSAR - Received Video", frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    self.running = False
                    break
                    
        except Exception as e:
            print(f"[CLIENT] Error handling connection: {e}")
        finally:
            client_sock.close()

    def output_server(self, host, port, name):
        """Generic output server for Dashboard and ROS."""
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server_sock.bind((host, port))
            server_sock.listen(1)
            print(f"[{name}] Listening on {host}:{port}")
        except Exception as e:
            print(f"[{name}] Failed to bind: {e}")
            return
            
        if name == "DASHBOARD":
            self.dashboard_socket = server_sock
        elif name == "ROS":
            self.ros_socket = server_sock

        while self.running:
            try:
                print(f"[{name}] Waiting for client...")
                # Use a timeout so we can exit cleanly if self.running becomes false
                server_sock.settimeout(1.0) 
                try:
                    client_sock, client_addr = server_sock.accept()
                except socket.timeout:
                    continue
                    
                print(f"[{name}] Connected: {client_addr}")
                client_sock.settimeout(2.0)
                
                # We need to send the latest frame when it arrives
                last_sent_frame = None
                try:
                    while self.running:
                        # Wait for a new frame
                        latest = self.buffer.wait_for_new_frame(timeout=0.5)
                        if latest is None or latest == last_sent_frame:
                            continue
                            
                        header_bytes, payload_bytes = latest
                        try:
                            client_sock.sendall(header_bytes)
                            client_sock.sendall(payload_bytes)
                            last_sent_frame = latest
                        except Exception as e:
                            print(f"[{name}] Client disconnected: {e}")
                            break # Break inner loop, wait for new client
                finally:
                    try:
                        client_sock.close()
                    except Exception:
                        pass
                        
            except Exception as e:
                if self.running:
                    print(f"[{name}] Server error: {e}")
                    
        server_sock.close()

    def start(self):
        """Starts the central TCP receiver."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        self.server_socket.settimeout(1.0)
        self.running = True

        # Start output servers
        threading.Thread(target=self.output_server, args=(DASHBOARD_HOST, DASHBOARD_PORT, "DASHBOARD"), daemon=True).start()
        threading.Thread(target=self.output_server, args=(ROS_HOST, ROS_PORT, "ROS"), daemon=True).start()

        print("[SERVER] Starting...")
        print(f"[SERVER] Listening on {self.host}:{self.port} for camera")

        try:
            while self.running:
                try:
                    client_sock, client_addr = self.server_socket.accept()
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"[SERVER] Error accepting connection: {e}")
                    continue

                print(f"[CLIENT] Connected: {client_addr}")
                self.handle_client(client_sock)
        except KeyboardInterrupt:
            print("\n[SERVER] Shutting down gracefully...")
        finally:
            self.stop()

    def stop(self):
        """Clean shutdown of the server."""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        if self.dashboard_socket:
            self.dashboard_socket.close()
        if self.ros_socket:
            self.ros_socket.close()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    server = VideoDistributorServer()
    server.start()
