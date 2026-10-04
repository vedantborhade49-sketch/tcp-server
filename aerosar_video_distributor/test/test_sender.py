"""
Later use the laptop webcam as a simulated Raspberry Pi camera.
It will send JPEG frames to the distributor through TCP.
"""

import cv2
import socket
import time
import sys
import os

# Add parent directory to path so we can import from distributor and config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import HOST, PORT, JPEG_QUALITY
from distributor.protocol import pack_header

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    frame_id = 1
    sock = None
    connected = False
    last_reconnect_time = 0.0

    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]

    print(f"Attempting to connect to distributor at {HOST}:{PORT}")
    
    fps_start_time = time.time()
    fps_frame_count = 0
    current_fps = 0

    while True:
        # We must continuously read from webcam to keep preview live
        # and prevent stale frames from building up in the hardware buffer
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture image from webcam.")
            break

        # Calculate FPS
        fps_frame_count += 1
        elapsed_time = time.time() - fps_start_time
        if elapsed_time >= 1.0:
            current_fps = fps_frame_count / elapsed_time
            fps_frame_count = 0
            fps_start_time = time.time()

        # Connection logic
        if not connected:
            current_time = time.time()
            if current_time - last_reconnect_time >= 1.0:
                last_reconnect_time = current_time
                if sock is not None:
                    sock.close()
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect((HOST, PORT))
                    connected = True
                    print(f"Successfully connected to the distributor at {HOST}:{PORT}!")
                except ConnectionRefusedError:
                    print(f"Connection error: Distributor at {HOST}:{PORT} is not running. Retrying...")
                    sock = None
                except Exception as e:
                    print(f"Connection error: {e}. Retrying...")
                    sock = None

        # Transmission logic
        if connected:
            try:
                # Encode as JPEG
                result, encoded_image = cv2.imencode('.jpg', frame, encode_param)
                if not result:
                    print("Failed to encode frame as JPEG.")
                    continue

                payload = encoded_image.tobytes()
                payload_size = len(payload)
                timestamp_ns = time.time_ns()
                height, width, _ = frame.shape

                # Create and send header
                header = pack_header(frame_id, timestamp_ns, payload_size, width, height)
                sock.sendall(header)
                
                # Send JPEG payload
                sock.sendall(payload)
                
                frame_id += 1

            except (ConnectionResetError, BrokenPipeError, socket.error) as e:
                print(f"Connection lost during transmission: {e}. Reconnecting...")
                connected = False
                if sock is not None:
                    sock.close()
                    sock = None

        # Display preview
        display_frame = frame.copy()
        status_text = "Connected" if connected else "Disconnected"
        status_color = (0, 255, 0) if connected else (0, 0, 255)

        cv2.putText(display_frame, f"Frame ID: {frame_id}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(display_frame, f"FPS: {current_fps:.1f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(display_frame, f"Status: {status_text}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)

        cv2.imshow("Test Sender Preview", display_frame)

        # Clean shutdown on 'Q' or 'q'
        if cv2.waitKey(1) & 0xFF in [ord('q'), ord('Q')]:
            print("Q pressed. Shutting down sender cleanly...")
            break

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    if sock is not None:
        sock.close()

if __name__ == "__main__":
    main()
