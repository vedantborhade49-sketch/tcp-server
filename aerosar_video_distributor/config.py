"""
AEROSAR - Central Configuration
All host, port, resolution, and encoding settings are kept here.
"""

# Server binding addresses
SERVER_HOST = "0.0.0.0"

# TCP Ports
PI_PORT = 5000
DASHBOARD_PORT = 6001
ROS_PORT = 6002

# Target Laptop IP for Pi / Clients to connect to
# Change this to your laptop's Wi-Fi / Ethernet LAN IP (e.g. "192.168.1.100") when running on Pi
LAPTOP_IP = "127.0.0.1"

# Video capture and encoding parameters
JPEG_QUALITY = 75
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
FPS_TARGET = 30

# Legacy compatibility aliases
VIDEO_HOST = SERVER_HOST
VIDEO_PORT = PI_PORT
DASHBOARD_HOST = LAPTOP_IP
ROS_HOST = LAPTOP_IP
HOST = SERVER_HOST
PORT = PI_PORT
