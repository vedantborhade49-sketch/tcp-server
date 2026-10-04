"""
AEROSAR - Raspberry Pi 5 Camera Sender Configuration

Contains network endpoints, camera properties, and compression settings.
Designed for low-latency transmission over Wi-Fi to the laptop distributor.
"""
import os

# Laptop Video Distributor IP and Port
# NOTE: Do NOT use 127.0.0.1 on the Raspberry Pi!
# Replace with your laptop's actual LAN / Wi-Fi IP address (e.g. 192.168.1.100).
# Can also be set via environment variable: export DISTRIBUTOR_HOST="192.168.1.X"
DISTRIBUTOR_HOST = os.getenv("DISTRIBUTOR_HOST", "192.168.1.100")
DISTRIBUTOR_PORT = int(os.getenv("DISTRIBUTOR_PORT", 5000))

# Camera Source Type:
# 'auto'   : Automatically detects Picamera2 (Raspberry Pi 5 official stack),
#            falls back to OpenCV USB webcam if Picamera2 is unavailable.
# 'picam2' : Enforce official Raspberry Pi Camera stack (Picamera2 / libcamera).
# 'opencv' : Enforce OpenCV VideoCapture (for USB cameras or development).
# 'test'   : Synthetic test pattern generator (no physical camera needed).
CAMERA_TYPE = os.getenv("CAMERA_TYPE", "auto")

# Camera Capture Parameters
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", 0))   # Used when CAMERA_TYPE is 'opencv'
FRAME_WIDTH = int(os.getenv("FRAME_WIDTH", 640))
FRAME_HEIGHT = int(os.getenv("FRAME_HEIGHT", 480))
FPS_TARGET = int(os.getenv("FPS_TARGET", 30))

# JPEG Compression Quality (1 - 100)
# 75 balances visual fidelity for YOLO/SLAM with minimal Wi-Fi packet size
JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", 75))

# Automatic Network Reconnection
RECONNECT_INTERVAL = float(os.getenv("RECONNECT_INTERVAL", 1.0))
