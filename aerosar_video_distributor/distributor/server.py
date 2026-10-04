"""
Backwards-compatibility runner for distributor/server.py -> server/video_server.py
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server.video_server import VideoServer

if __name__ == "__main__":
    server = VideoServer()
    server.start()
