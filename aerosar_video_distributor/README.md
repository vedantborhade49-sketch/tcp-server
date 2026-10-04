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

## Configuration (`config.py`)

All communication ports are fully configurable in `config.py`:
- `VIDEO_HOST = "0.0.0.0"` / `VIDEO_PORT = 5000` (Camera TCP ingestion)
- `DASHBOARD_HOST = "127.0.0.1"` / `DASHBOARD_PORT = 6001` (Dashboard TCP stream)
- `ROS_HOST = "127.0.0.1"` / `ROS_PORT = 6002` (ROS TCP bridge stream)

---

## How to Run the STAGE 5 Three-Side Test

Ensure your virtual environment (`.venv` or `venv`) is activated in each terminal:
```powershell
.\venv\Scripts\Activate.ps1
```

### SIDE 1: Main Sender + Central Video Distributor
Run the combined launcher from the project directory:
```bash
python run_test.py
```
*(From workspace root: `python run_test.py` or `python aerosar_video_distributor/run_test.py`)*

This starts `distributor/server.py` and `test/test_sender.py` concurrently.

### SIDE 2: Dashboard TCP Receiver
In a second terminal:
```bash
python clients/dashboard_client.py
```
*(From workspace root: `python aerosar_video_distributor/clients/dashboard_client.py`)*

### SIDE 3: ROS TCP Receiver & Bridge
In a third terminal:
```bash
python clients/ros_client.py
```
*(From workspace root: `python aerosar_video_distributor/clients/ros_client.py`)*

---

## Expected Output & Verification

Both receivers receive identical frames and print matching Frame IDs:

**SIDE 2 (Dashboard):**
```text
[DASHBOARD] Frame ID=152 | 640x480 | 30.0 FPS
[DASHBOARD] Frame ID=153 | 640x480 | 30.0 FPS
```

**SIDE 3 (ROS Bridge):**
```text
[ROS] Frame ID=152 | 640x480 | 30.0 FPS
[ROS] Frame ID=153 | 640x480 | 30.0 FPS
```

Press `Q` in any video window or `Ctrl+C` in any terminal to shut down cleanly.

