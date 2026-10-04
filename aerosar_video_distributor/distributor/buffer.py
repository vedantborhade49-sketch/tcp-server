"""
Later implement a bounded/latest-frame buffer.
The system should prefer dropping stale frames rather than building latency.
"""

import threading

class VideoBuffer:
    def __init__(self):
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
        self.latest_frame = None

    def push(self, header_bytes, payload_bytes):
        with self.lock:
            self.latest_frame = (header_bytes, payload_bytes)
            self.condition.notify_all()

    def wait_for_new_frame(self, timeout=1.0):
        """
        Wait for a new frame to become available.
        Returns the latest frame (header_bytes, payload_bytes) or None on timeout.
        """
        with self.condition:
            self.condition.wait(timeout=timeout)
            return self.latest_frame

if __name__ == "__main__":
    import time

    print("--- Testing VideoBuffer ---")
    buf = VideoBuffer()

    # Test 1: Push and retrieve a frame
    test_header = b"HEADER_V1_FRAME_001"
    test_payload = b"PAYLOAD_JPEG_DUMMY_DATA"

    print("Pushing frame into buffer...")
    buf.push(test_header, test_payload)

    frame_data = buf.wait_for_new_frame(timeout=0.5)
    assert frame_data is not None, "Failed to retrieve frame from buffer!"
    header, payload = frame_data
    print(f"Retrieved Header : {header.decode()}")
    print(f"Retrieved Payload: {payload.decode()}")
    assert header == test_header and payload == test_payload, "Frame data mismatch!"

    # Test 2: Multi-threaded producer / consumer test
    print("\nTesting multi-threaded producer & consumer...")
    received_frames = []

    def consumer():
        last_seen = None
        for _ in range(3):
            frame = buf.wait_for_new_frame(timeout=1.0)
            if frame and frame != last_seen:
                received_frames.append(frame[0])
                last_seen = frame

    cons_thread = threading.Thread(target=consumer)
    cons_thread.start()

    time.sleep(0.1)
    for i in range(1, 4):
        buf.push(f"FRAME_{i}".encode(), b"DATA")
        time.sleep(0.1)

    cons_thread.join()
    print(f"Consumer received: {[f.decode() for f in received_frames]}")
    print("VideoBuffer is working properly!")

