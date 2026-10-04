"""
AEROSAR - Camera Capture Abstraction for Raspberry Pi & Local Development

Provides a unified interface:
    class CameraSource:
        def open() -> bool
        def read() -> Tuple[bool, Optional[np.ndarray]]
        def release() -> None

Supports:
1. Raspberry Pi Camera (Picamera2 / libcamera)
2. USB webcam (OpenCV VideoCapture)
3. Synthetic test frames (fallback when no physical camera is attached)
"""
import time
from typing import Tuple, Optional
import numpy as np
import cv2


class CameraSource:
    """
    Hardware-agnostic camera capture source.
    Decouples camera drivers from TCP network streaming.
    """
    def __init__(
        self,
        camera_type: str = "auto",
        width: int = 1280,
        height: int = 720,
        fps: int = 30,
        camera_index: int = 0
    ):
        self.camera_type = camera_type.lower().strip()
        self.width = width
        self.height = height
        self.fps = fps
        self.camera_index = camera_index

        self.backend: Optional[str] = None
        self.cap: Optional[cv2.VideoCapture] = None
        self.picam2 = None
        self.frame_count: int = 0
        self.is_open: bool = False

    def open(self) -> bool:
        """
        Initializes and opens the camera.
        Returns True on success, False on failure.
        """
        self.release()

        # 1. Explicit or auto Picamera2 (Raspberry Pi 5)
        if self.camera_type in ["auto", "picam2"]:
            try:
                from picam2 import Picamera2  # type: ignore
                print(f"[CAMERA] Initializing Picamera2 ({self.width}x{self.height} @ {self.fps} FPS)...")
                self.picam2 = Picamera2()
                video_config = self.picam2.create_video_configuration(
                    main={"format": "BGR888", "size": (self.width, self.height)},
                    controls={"FrameRate": self.fps}
                )
                self.picam2.configure(video_config)
                self.picam2.start()
                self.backend = "picam2"
                self.is_open = True
                print("[CAMERA] Raspberry Pi Camera (Picamera2) opened successfully.")
                return True
            except (ImportError, ModuleNotFoundError):
                if self.camera_type == "picam2":
                    print("[CAMERA] Error: Picamera2 is not installed.")
                    return False
            except Exception as e:
                print(f"[CAMERA] Picamera2 init failed: {e}")
                if self.camera_type == "picam2":
                    return False

        # 2. Explicit or fallback OpenCV (USB webcam)
        if self.camera_type in ["auto", "opencv"]:
            try:
                print(f"[CAMERA] Opening OpenCV VideoCapture index {self.camera_index}...")
                self.cap = cv2.VideoCapture(self.camera_index)
                if self.cap.isOpened():
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    self.cap.set(cv2.CAP_PROP_FPS, self.fps)
                    self.backend = "opencv"
                    self.is_open = True
                    print(f"[CAMERA] OpenCV camera {self.camera_index} opened successfully.")
                    return True
                else:
                    self.cap.release()
                    self.cap = None
                    if self.camera_type == "opencv":
                        print(f"[CAMERA] Error: Could not open camera {self.camera_index}.")
                        return False
            except Exception as e:
                print(f"[CAMERA] OpenCV camera init failed: {e}")
                if self.camera_type == "opencv":
                    return False

        # 3. Synthetic test source fallback
        print("[CAMERA] No physical camera found. Using Synthetic Test Generator.")
        self.backend = "test"
        self.is_open = True
        self.frame_count = 0
        return True

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Captures a single frame.
        Returns: (True, frame) on success, (False, None) on failure.
        """
        if not self.is_open:
            return False, None

        if self.backend == "picam2" and self.picam2 is not None:
            try:
                frame = self.picam2.capture_array()
                if frame is not None and (frame.shape[1] != self.width or frame.shape[0] != self.height):
                    frame = cv2.resize(frame, (self.width, self.height))
                return True, frame
            except Exception as e:
                print(f"[CAMERA] Picamera2 capture error: {e}")
                return False, None

        if self.backend == "opencv" and self.cap is not None:
            ret, frame = self.cap.read()
            if not ret or frame is None:
                return False, None
            if frame.shape[1] != self.width or frame.shape[0] != self.height:
                frame = cv2.resize(frame, (self.width, self.height))
            return True, frame

        if self.backend == "test":
            self.frame_count += 1
            # Generate synthetic test pattern
            frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            frame[:] = (35, 35, 35)

            # Draw moving indicator
            box_x = int((self.frame_count * 10) % (self.width - 120))
            box_y = int(self.height / 2 - 60)
            cv2.rectangle(frame, (box_x, box_y), (box_x + 120, box_y + 120), (0, 215, 255), -1)

            cv2.putText(
                frame, "AEROSAR PI CAMERA SOURCE",
                (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2
            )
            cv2.putText(
                frame, f"Frame: {self.frame_count} | {time.strftime('%H:%M:%S')}",
                (30, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2
            )
            return True, frame

        return False, None

    def release(self) -> None:
        """Releases camera hardware and resources."""
        if self.picam2 is not None:
            try:
                self.picam2.stop()
                self.picam2.close()
            except Exception:
                pass
            self.picam2 = None

        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

        self.backend = None
        self.is_open = False
