import socket
import sys
import os
import cv2
import numpy as np
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LAPTOP_IP, ROS_PORT, FRAME_TIMEOUT
from protocol import read_packet

def ros_publish_offline():
    """
    Tells ROS that the camera is currently offline.
    """
    pass

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
            sock.settimeout(0.5)
            
            frames_received = 0
            last_frame_time = time.time()
            camera_online = False
            
            while True:
                try:
                    packet_data = read_packet(sock)
                    if not packet_data:
                        break
                except (socket.timeout, TimeoutError):
                    packet_data = None
                    
                current_time = time.time()
                
                if packet_data:
                    frame_id, timestamp, jpeg_bytes, raw_packet = packet_data
                    frames_received += 1
                    last_frame_time = current_time
                    camera_online = True
                    
                    if frames_received % 30 == 0:
                        print(f"[ROS] Frame {frame_id} received")
                        
                    # Decode frame
                    frame = cv2.imdecode(np.frombuffer(jpeg_bytes, np.uint8), cv2.IMREAD_COLOR)
                    
                    # Pass to ROS integration
                    ros_publish_frame(frame)
                else:
                    if current_time - last_frame_time > FRAME_TIMEOUT:
                        if camera_online:
                            print("[ROS] CAMERA OFFLINE")
                        camera_online = False
                        ros_publish_offline()
                
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
