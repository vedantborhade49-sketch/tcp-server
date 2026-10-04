"""
AEROSAR - SIDE 3: Python ROS TCP Receiver & Bridge.

Flow:
TCP connection
  ↓
receive packet
  ↓
decode JPEG
  ↓
OpenCV frame
  ↓
ROS integration layer (ROSImagePublisher)
  ↓
ROS image topic (/camera/image_raw)
  ↓
Existing ROS / SLAM system
"""
import sys
import os
import socket
import time
import cv2
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ROS_HOST, ROS_PORT
from distributor.protocol import HEADER_SIZE, unpack_header


class ROSImagePublisher:
    """
    ROS integration layer.
    Bridges received OpenCV frames into the existing ROS/SLAM system via ROS image topics.
    When ROS is not installed in the local environment (e.g. laptop development .venv),
    gracefully falls back to standalone TCP receiver mode without error.
    """
    def __init__(self, topic_name="/camera/image_raw"):
        self.topic_name = topic_name
        self.ros_available = False
        self.publisher = None
        self.bridge = None
        self._init_ros()

    def _init_ros(self):
        # 1. Attempt ROS 1 (rospy) integration
        try:
            import rospy  # type: ignore
            from sensor_msgs.msg import Image  # type: ignore
            from cv_bridge import CvBridge  # type: ignore

            if not rospy.core.is_initialized():
                rospy.init_node("aerosar_video_bridge", anonymous=True)
            self.bridge = CvBridge()
            self.publisher = rospy.Publisher(self.topic_name, Image, queue_size=1)
            self.ros_available = True
            print(f"[ROS BRIDGE] Initialized ROS 1 node. Publishing to {self.topic_name}")
            return
        except ImportError:
            pass

        # 2. Attempt ROS 2 (rclpy) next
        try:
            import rclpy  # type: ignore
            from sensor_msgs.msg import Image  # type: ignore
            from cv_bridge import CvBridge  # type: ignore

            if not rclpy.ok():
                rclpy.init()
            self.node = rclpy.create_node("aerosar_video_bridge")
            self.bridge = CvBridge()
            self.publisher = self.node.create_publisher(Image, self.topic_name, 1)
            self.ros_available = True
            print(f"[ROS BRIDGE] Initialized ROS 2 node. Publishing to {self.topic_name}")
            return
        except ImportError:
            pass

        print(f"[ROS BRIDGE] Standalone mode (ROS/rospy not loaded in this environment). Ready for ROS integration.")

    def publish_frame(self, cv_frame, frame_id, timestamp_ns):
        """Passes the decoded frame to the ROS topic for consumption by existing ROS/SLAM."""
        if not self.ros_available or self.publisher is None:
            return

        try:
            img_msg = self.bridge.cv2_to_imgmsg(cv_frame, encoding="bgr8")
            if hasattr(img_msg, 'header'):
                img_msg.header.seq = frame_id
                img_msg.header.stamp.secs = int(timestamp_ns // 1_000_000_000)
                img_msg.header.stamp.nsecs = int(timestamp_ns % 1_000_000_000)
                img_msg.header.frame_id = "camera_link"
            self.publisher.publish(img_msg)
        except Exception as e:
            print(f"[ROS BRIDGE] Error publishing frame to ROS: {e}")


def receive_exact(sock, size):
    data = bytearray()
    while len(data) < size:
        packet = sock.recv(size - len(data))
        if not packet:
            raise ConnectionError("Connection closed")
        data.extend(packet)
    return bytes(data)


def run():
    print(f"[ROS] Starting TCP Receiver connecting to {ROS_HOST}:{ROS_PORT}...")
    ros_bridge = ROSImagePublisher(topic_name="/camera/image_raw")

    while True:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((ROS_HOST, ROS_PORT))
            print(f"[ROS] Connected to {ROS_HOST}:{ROS_PORT}")
        except Exception as e:
            print(f"[ROS] Waiting for distributor at {ROS_HOST}:{ROS_PORT}... ({e})")
            time.sleep(1.0)
            continue

        frames_received = 0
        start_time = time.time()

        try:
            while True:
                # 1. Receive standard protocol header
                header_bytes = receive_exact(sock, HEADER_SIZE)
                frame_id, timestamp_ns, payload_size, width, height = unpack_header(header_bytes)

                # 2. Receive JPEG payload
                payload_bytes = receive_exact(sock, payload_size)

                # 3. Decode JPEG to OpenCV frame
                frame_data = np.frombuffer(payload_bytes, dtype=np.uint8)
                frame = cv2.imdecode(frame_data, cv2.IMREAD_COLOR)

                if frame is None:
                    continue

                # 4. Pass frame to ROS integration layer for existing ROS/SLAM
                ros_bridge.publish_frame(frame, frame_id, timestamp_ns)

                frames_received += 1
                elapsed = time.time() - start_time
                fps = frames_received / elapsed if elapsed > 0 else 0

                print(f"[ROS] Frame ID={frame_id} | {width}x{height} | {fps:.1f} FPS")

                # 5. Display visual preview
                cv2.putText(frame, f"ROS Frame ID: {frame_id}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.putText(frame, f"FPS: {fps:.1f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.imshow("AEROSAR - ROS Receiver", frame)

                if cv2.waitKey(1) & 0xFF in [ord('q'), ord('Q')]:
                    print("[ROS] Shutdown requested by user.")
                    return
        except Exception as e:
            print(f"[ROS] Disconnected: {e}. Reconnecting in 1s...")
            time.sleep(1.0)
        finally:
            try:
                sock.close()
            except Exception:
                pass
            cv2.destroyAllWindows()


if __name__ == "__main__":
    run()
