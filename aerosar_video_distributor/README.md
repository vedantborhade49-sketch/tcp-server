# AEROSAR - Simplified Video Transport System

A lightweight, robust TCP-based video transmission system designed to transport video frames from a Raspberry Pi Camera to a central Laptop Video Server, which distributes the raw JPEG frames directly to a Dashboard and ROS without re-encoding overhead.

---

## Architecture

```text
             RASPBERRY PI
                  │
             CameraSource (Picamera2 / OpenCV / Fallback)
                  │
                 JPEG
                  │
                 TCP
                  │
                  ▼
         ┌─────────────────┐
         │  LAPTOP SERVER  │
         │                 │
         │  TCP :5000      │
         └───────┬─────────┘
                 │
          ┌──────┴──────┐
          │             │
       TCP :6001     TCP :6002
          │             │
          ▼             ▼
      DASHBOARD        ROS
      RECEIVER      RECEIVER
          │             │
          ▼             ▼
     Existing CV   Existing SLAM
       + YOLO
```

---

## Network Ports

| Component | Port | Description |
|---|---|---|
| **Pi Video Input** | `5000` | Accepts 1 connection from Raspberry Pi sender |
| **Dashboard Output** | `6001` | Forwards original JPEG frames to Dashboard |
| **ROS Output** | `6002` | Forwards original JPEG frames to ROS/SLAM bridge |

---

## 16-Byte Packet Protocol (`protocol.py`)

All packets use a simple, length-prefixed binary format in **big-endian (network byte order)**:

```text
[4 bytes frame_id]     -> uint32 (">I")
[8 bytes timestamp]    -> uint64 (">Q", integer milliseconds)
[4 bytes payload_size] -> uint32 (">I")
[JPEG payload bytes]   -> raw JPEG bytes
```
- **Total Header Size**: 16 bytes.
- Zero serialization overhead (no JSON, no pickle, no dicts).
- Zero server re-encoding: the server passes the exact incoming JPEG packet straight to connected clients.

---

## Directory Structure

```text
aerosar_video_distributor/
├── server/
│   └── video_server.py       # Central Laptop TCP Server
├── clients/
│   ├── dashboard_client.py   # Dashboard TCP Receiver
│   └── ros_client.py         # ROS TCP Receiver & Bridge
├── pi/
│   ├── camera_source.py      # Hardware-agnostic Camera capture abstraction
│   └── sender.py             # Raspberry Pi Camera Sender
├── test/
│   └── fake_sender.py        # Laptop synthetic video test sender
├── protocol.py               # 16-byte length-prefixed packet protocol
├── config.py                 # Central network and video settings
├── requirements.txt          # Minimal dependencies
└── README.md
```

---

## Progressive Testing Guide

### TEST 1: Laptop Video Server + Fake Sender
Verify that sender frames reach the server over TCP.

**Terminal 1 (Server):**
```bash
python aerosar_video_distributor/server/video_server.py
```
**Terminal 2 (Fake Sender):**
```bash
python aerosar_video_distributor/test/fake_sender.py
```
*Expected Console Output:*
- Server: `[SERVER] Pi connected`, `[SERVER] Frame 30 received`
- Sender: `[FAKE SENDER] Connected to server at 127.0.0.1:5000`, `[FAKE SENDER] Sent frame 30`

---

### TEST 2: Server + Dashboard Receiver
Verify that frames flow from server to the Dashboard preview.

**Terminal 1 (Server):**
```bash
python aerosar_video_distributor/server/video_server.py
```
**Terminal 2 (Fake Sender):**
```bash
python aerosar_video_distributor/test/fake_sender.py
```
**Terminal 3 (Dashboard Receiver):**
```bash
python aerosar_video_distributor/clients/dashboard_client.py
```
*Expected Result:*
- Window opens displaying animated video frames with frame counter and timestamp.
- Console: `[DASHBOARD] Connected`, `[DASHBOARD] Frame 30 received`.

---

### TEST 3: Server + ROS Receiver
Verify that frames flow from server to the ROS receiver integration point.

**Terminal 1 (Server):**
```bash
python aerosar_video_distributor/server/video_server.py
```
**Terminal 2 (Fake Sender):**
```bash
python aerosar_video_distributor/test/fake_sender.py
```
**Terminal 3 (ROS Receiver):**
```bash
python aerosar_video_distributor/clients/ros_client.py
```
*Expected Result:*
- Window opens displaying the ROS video stream.
- Console: `[ROS] Connected`, `[ROS] Frame 30 received`.

---

### TEST 4: Run All Three Sides Simultaneously
Verify full distribution pipeline with 1 sender and 2 receivers.

**Option A - Automated Launcher:**
```bash
python run_all.py
```

**Option B - Manual Terminals:**
1. Start Server: `python aerosar_video_distributor/server/video_server.py`
2. Start Dashboard: `python aerosar_video_distributor/clients/dashboard_client.py`
3. Start ROS: `python aerosar_video_distributor/clients/ros_client.py`
4. Start Sender: `python aerosar_video_distributor/test/fake_sender.py`

---

### TEST 5: Real Raspberry Pi Camera
Deploy to actual Raspberry Pi hardware.

1. On Raspberry Pi, configure `config.py` with your laptop's LAN IP:
   ```python
   LAPTOP_IP = "192.168.1.100"  # Replace with actual laptop IP
   ```
2. On Laptop, start Video Server:
   ```bash
   python aerosar_video_distributor/server/video_server.py
   ```
3. On Raspberry Pi, run sender:
   ```bash
   python aerosar_video_distributor/pi/sender.py --host 192.168.1.100
   ```
