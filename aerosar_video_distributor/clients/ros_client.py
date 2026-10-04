import socket
import sys
import os
import cv2
import numpy as np
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LAPTOP_IP, ROS_PORT
from protocol import read_packet

def ros_publish_frame(frame):
    """
    Clean integration point for existing ROS / SLAM code.
    Connect this function to your actual ROS 1 or ROS 2 publishers.
    """
    # ----- EXISTING ROS/SLAM INTEGRATION GOES HERE -----
    pass

def run_ros_client():
    while True:
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((LAPTOP_IP, ROS_PORT))
            print("[ROS] Connected")
            
            frames_received = 0
            while True:
                packet_data = read_packet(sock)
                if not packet_data:
                    break
                    
                frame_id, timestamp, jpeg_bytes = packet_data
                frames_received += 1
                
                if frames_received % 30 == 0:
                    print(f"[ROS] Frame {frame_id} received")
                    
                # Decode frame
                frame = cv2.imdecode(np.frombuffer(jpeg_bytes, np.uint8), cv2.IMREAD_COLOR)
                
                # Pass to ROS integration
                ros_publish_frame(frame)
                
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

if __name__ == "__main__":
    run_ros_client()
