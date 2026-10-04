# AEROSAR Video Distributor

This project is the central Python video distributor module. It receives video frames and routes them to the dashboard and ROS bridge.

## Target Architecture

```text
Laptop/Webcam test sender
|
| TCP
v
Central Python Video Distributor
|
+------ TCP ------> Existing Python Dashboard
|
+------ TCP ------> ROS Video Bridge
|
v
Existing ROS/SLAM
```

Eventually, the webcam/test sender will be replaced by a Raspberry Pi 5 camera sender.

## Modules

- `distributor/`: Core components (TCP server, protocol format, buffer).
- `clients/`: Handlers for external systems (Dashboard, ROS).
- `test/`: Emulators like the webcam test sender.

## How to Install Dependencies

Currently, the sender requires OpenCV.
Install the dependencies using pip:
```bash
pip install -r requirements.txt
```
Alternatively, install opencv manually:
```bash
pip install opencv-python
```

## How to Run the Test Sender

For STAGE 3, we have implemented the test sender which uses your laptop webcam to temporarily simulate the Raspberry Pi camera.

**What the sender does:**
- Opens the local laptop webcam.
- Displays a live preview of the video with overlay stats (FPS, Connection Status, Frame ID).
- Encodes the frames into JPEG format.
- Attempts to connect to the central distributor via TCP (using host and port defined in `config.py`, default `127.0.0.1:8000`).
- Once connected, continuously transmits the packet header and JPEG payload.
- Automatically handles connection drops without queuing stale frames.

Run the test sender from the project root with:
```bash
python test/test_sender.py
```

*Note: STAGE 4 is now implemented! See below for the end-to-end testing procedure.*

## How to Run the STAGE 4 Receiver Test

For STAGE 4, we have implemented the central video distributor receiver. To test the connection:

**Terminal 1 (Start the Server):**
```bash
python distributor/server.py
```

**Terminal 2 (Start the Sender):**
```bash
python test/test_sender.py
```

**Expected result:**

Terminal 1 should log the incoming connection and frames:
```text
[SERVER] Starting...
[SERVER] Listening on 127.0.0.1:8000
[CLIENT] Connected: ('127.0.0.1', 54321)
[FRAME] ID=1 | 640x480 | 28.4 FPS | 35.2 ms
[FRAME] ID=2 | 640x480 | 29.1 FPS | 34.8 ms
[FRAME] ID=3 | 640x480 | 29.8 FPS | 36.1 ms
...
```

An OpenCV window named `AEROSAR - Received Video` should open and display the live webcam stream received through TCP, complete with overlaid telemetry metrics (Frame ID, FPS, Resolution, and Latency).

This proves the following data flow:
Camera → JPEG encoding → TCP → Distributor → JPEG decoding → OpenCV frame

(Press `Q` in the OpenCV window to cleanly shut down the receiver)
