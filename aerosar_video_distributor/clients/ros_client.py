"""
AEROSAR - ROS Video Receiver (Client & Bridge)

Connects to Laptop Video Server on TCP 6002.
Pipeline:
  receive_frame()
        ↓
  decode_frame()
        ↓
  ros_publish_frame()

Does NOT modify SLAM.
Provides a clean, modular integration point for ROS 1 / ROS 2 environments.
"""
import sys
import os
import socket
import time
from typing import Optional, Tuple
import numpy as np
import cv2

# Add parent directory to path to import protocol and config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LAPTOP_IP, ROS_PORT
from protocol import read_header, read_exact


# ==============================================================================
# ROS Integration Point
# ==============================================================================
class ROSIntegration:
    """
    Modular ROS bridge.
    Detects whether ROS 1 (rospy) or ROS 2 (rclpy) is available.
    If neither is detected (e.g. running on Windows laptop .venv),
    operates safely in standalone mode without raising errors.
    """
    def __init__(self, topic: str = "/camera/image_raw"):
        self.topic = topic
        self.ros_type = None
        self.publisher = None
        self.bridge = None
        self.node = None
        self._init_ros()

    def _init_ros(self) -> None:
        # Check for ROS 1 (rospy)
        try:
            import rospy  # type: ignore
            from sensor_msgs.msg import Image  # type: ignore
            from cv_bridge import CvBridge  # type: ignore

            if not rospy.core.is_initialized():
                rospy.init_node("aerosar_video_client", anonymous=True)
            self.bridge = CvBridge()
            self.publisher = rospy.Publisher(self.topic, Image, queue_size=1)
            self.ros_type = "ROS 1"
            print(f"[ROS BRIDGE] Initialized ROS 1 node publishing to {self.topic}")
            return
        except (ImportError, ModuleNotFoundError):
            pass

        # Check for ROS 2 (rclpy)
        try:
            import rclpy  # type: ignore
            from sensor_msgs.msg import Image  # type: ignore
            from cv_bridge import CvBridge  # type: ignore

            if not rclpy.ok():
                rclpy.init()
            self.node = rclpy.create_node("aerosar_video_client")
            self.bridge = CvBridge()
            self.publisher = self.node.create_publisher(Image, self.topic, 1)
            self.ros_type = "ROS 2"
            print(f"[ROS BRIDGE] Initialized ROS 2 node publishing to {self.topic}")
            return
        except (ImportError, ModuleNotFoundError):
            pass

        print("[ROS BRIDGE] Standalone mode (ROS not detected in current environment).")
        print("[ROS BRIDGE] Frame is ready for SLAM/ROS in `ros_publish_frame()`.")


_ros_integration: Optional[ROSIntegration] = None


def ros_publish_frame(frame: np.ndarray, frame_id: int, timestamp: int) -> None:
    """
    Clean ROS integration hook.
    Connect your SLAM / ROS image pipeline here.
    """
    global _ros_integration
    if _ros_integration is None:
        _ros_integration = ROSIntegration()

    if _ros_integration.ros_type == "ROS 1" and _ros_integration.publisher and _ros_integration.bridge:
        try:
            msg = _ros_integration.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
            if hasattr(msg, "header"):
                msg.header.seq = frame_id
                # Handle timestamp in seconds/nanoseconds
                if timestamp > 1_000_000_000_000_000:  # nanoseconds
                    msg.header.stamp.secs = int(timestamp // 1_000_000_000)
                    msg.header.stamp.nsecs = int(timestamp % 1_000_000_000)
                else:  # milliseconds
                    msg.header.stamp.secs = int(timestamp // 1000)
                    msg.header.stamp.nsecs = int((timestamp % 1000) * 1_000_000)
                msg.header.frame_id = "camera_link"
            _ros_integration.publisher.publish(msg)
        except Exception as e:
            print(f"[ROS] Publish error: {e}")

    elif _ros_integration.ros_type == "ROS 2" and _ros_integration.publisher and _ros_integration.bridge:
        try:
            msg = _ros_integration.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
            _ros_integration.publisher.publish(msg)
        except Exception as e:
            print(f"[ROS] Publish error: {e}")


# ==============================================================================
# Network Pipeline: receive -> decode -> publish
# ==============================================================================
def receive_frame(sock: socket.socket) -> Tuple[int, int, bytes]:
    """Receives 16-byte header and exact JPEG payload."""
    frame_id, timestamp, payload_size = read_header(sock)
    jpeg_bytes = read_exact(sock, payload_size)
    return frame_id, timestamp, jpeg_bytes


def decode_frame(jpeg_bytes: bytes) -> Optional[np.ndarray]:
    """Decodes JPEG byte array into an OpenCV BGR frame."""
    frame_data = np.frombuffer(jpeg_bytes, dtype=np.uint8)
    return cv2.imdecode(frame_data, cv2.IMREAD_COLOR)


def run(host: str = LAPTOP_IP, port: int = ROS_PORT) -> None:
    """Main receiver loop connecting to the Video Server."""
    print(f"[ROS] Starting TCP Receiver connecting to {host}:{port}...")

    # Initialize ROS bridge
    global _ros_integration
    _ros_integration = ROSIntegration()

    sock: Optional[socket.socket] = None

    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.connect((host, port))
            print("[ROS] Connected")
        except Exception:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass
                sock = None
            time.sleep(1.0)
            continue

        frame_counter = 0

        try:
            while True:
                # 1. Receive
                frame_id, timestamp, jpeg_bytes = receive_frame(sock)

                # 2. Decode
                frame = decode_frame(jpeg_bytes)
                if frame is None:
                    continue

                # 3. Publish to ROS
                ros_publish_frame(frame, frame_id, timestamp)

                frame_counter += 1
                if frame_counter % 30 == 0:
                    print(f"[ROS] Frame {frame_id} received")

                # Visual preview
                cv2.imshow("AEROSAR - ROS Receiver", frame)
                if cv2.waitKey(1) & 0xFF in [ord('q'), ord('Q')]:
                    print("[ROS] Quit requested by user.")
                    return

        except (ConnectionError, socket.error):
            print("[ROS] Disconnected from server. Reconnecting in 1s...")
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass
                sock = None
            cv2.destroyAllWindows()
            time.sleep(1.0)


if __name__ == "__main__":
    target_host = sys.argv[1] if len(sys.argv) > 1 else LAPTOP_IP
    run(host=target_host)
