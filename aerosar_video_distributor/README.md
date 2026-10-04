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

*Note: STAGE 4 will implement the actual distributor receiver, so at this stage you will see "Connection Refused" messages from the sender as it waits for the server to come online.*
