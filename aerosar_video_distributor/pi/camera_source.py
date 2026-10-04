import cv2
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import FRAME_WIDTH, FRAME_HEIGHT

class CameraSource:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = None

    def open(self):
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            return False
            
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        return True

    def read(self):
        if not self.cap:
            return False, None
        return self.cap.read()
        
    def release(self):
        if self.cap:
            self.cap.release()
            self.cap = None
