"""
AEROSAR - Master 3-Side Test Launcher

Launches the complete three-side architecture simultaneously in dedicated console windows:
  SIDE 1: Main Sender + Video Distributor (run_test.py)
  SIDE 2: Dashboard TCP Receiver (clients/dashboard_client.py)
  SIDE 3: ROS TCP Receiver (clients/ros_client.py)
"""
import sys
import os
import time
import subprocess

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    python_exe = sys.executable

    # Verify venv executable preference if available
    venv_py = os.path.join(root_dir, "venv", "Scripts", "python.exe")
    if os.path.exists(venv_py):
        python_exe = venv_py

    side1_script = os.path.join(root_dir, "run_test.py")
    side2_script = os.path.join(root_dir, "aerosar_video_distributor", "clients", "dashboard_client.py")
    side3_script = os.path.join(root_dir, "aerosar_video_distributor", "clients", "ros_client.py")

    print("==================================================================")
    print("       AEROSAR - Master Test Launcher (All 3 Sides)               ")
    print("==================================================================")
    print(f"[*] Python Interpreter : {python_exe}")
    print(f"[*] Launching Side 1   : Main Sender + Distributor")
    print(f"[*] Launching Side 2   : Dashboard TCP Receiver")
    print(f"[*] Launching Side 3   : ROS TCP Receiver")
    print("==================================================================")

    # Windows flag to spawn each process in its own separate command window
    creation_flags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0

    # 1. Launch Side 1 (Distributor Server + Webcam Sender)
    side1_proc = subprocess.Popen([python_exe, side1_script], creationflags=creation_flags)
    print("[+] Side 1 started in a new console window.")

    # Give the distributor server 1.5s to bind ports (5000, 6001, 6002)
    time.sleep(1.5)

    # 2. Launch Side 2 (Dashboard Receiver)
    side2_proc = subprocess.Popen([python_exe, side2_script], creationflags=creation_flags)
    print("[+] Side 2 (Dashboard) started in a new console window.")

    time.sleep(0.5)

    # 3. Launch Side 3 (ROS Receiver)
    side3_proc = subprocess.Popen([python_exe, side3_script], creationflags=creation_flags)
    print("[+] Side 3 (ROS) started in a new console window.")

    print("\n[ALL SIDES ACTIVE]")
    print("Three separate windows are running. Press Ctrl+C in this master terminal to stop all sides.\n")

    try:
        while True:
            # Check if all processes have exited
            p1 = side1_proc.poll()
            p2 = side2_proc.poll()
            p3 = side3_proc.poll()
            if p1 is not None and p2 is not None and p3 is not None:
                print("[*] All processes have exited.")
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[*] Stopping all processes...")
    finally:
        for proc, name in [(side3_proc, "Side 3 (ROS)"), (side2_proc, "Side 2 (Dashboard)"), (side1_proc, "Side 1 (Distributor)")]:
            if proc.poll() is None:
                print(f"[*] Terminating {name}...")
                proc.terminate()
                try:
                    proc.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
        print("[*] All processes terminated successfully.")

if __name__ == "__main__":
    main()
