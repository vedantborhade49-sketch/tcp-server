"""
AEROSAR - SIDE 1 Launcher: Main Sender + Video Distributor.

Starts distributor/server.py and test/test_sender.py as separate processes,
managing their execution together in a single terminal for the three-sided test.
"""
import sys
import os
import time
import subprocess

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.join(base_dir, "distributor", "server.py")
    sender_script = os.path.join(base_dir, "test", "test_sender.py")

    # If running from outside the project directory
    if not os.path.exists(server_script):
        candidate_dir = os.path.join(base_dir, "aerosar_video_distributor")
        if os.path.exists(os.path.join(candidate_dir, "distributor", "server.py")):
            base_dir = candidate_dir
            server_script = os.path.join(base_dir, "distributor", "server.py")
            sender_script = os.path.join(base_dir, "test", "test_sender.py")

    python_executable = sys.executable

    print("==================================================================")
    print("       AEROSAR - SIDE 1: Main Sender + Video Distributor          ")
    print("==================================================================")
    print(f"[*] Python Interpreter: {python_executable}")
    print(f"[*] Starting Central Distributor Server: {server_script}")
    server_proc = subprocess.Popen([python_executable, server_script])

    # Allow distributor server a moment to bind ports (5000, 6001, 6002)
    time.sleep(1.0)

    print(f"[*] Starting Webcam Test Sender: {sender_script}")
    sender_proc = subprocess.Popen([python_executable, sender_script])

    print("\n[SIDE 1] Both Distributor and Sender are active.")
    print("[SIDE 1] Press Ctrl+C in this terminal to shut down both cleanly.\n")

    try:
        while True:
            # Monitor both child processes
            if server_proc.poll() is not None:
                print(f"\n[SIDE 1] Distributor server exited (code {server_proc.returncode}).")
                break
            if sender_proc.poll() is not None:
                print(f"\n[SIDE 1] Webcam sender exited (code {sender_proc.returncode}).")
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[SIDE 1] Shutdown signal received.")
    finally:
        for proc, name in [(sender_proc, "Webcam Sender"), (server_proc, "Distributor Server")]:
            if proc.poll() is None:
                print(f"[SIDE 1] Terminating {name}...")
                proc.terminate()
                try:
                    proc.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
        print("[SIDE 1] Shutdown complete.")

if __name__ == "__main__":
    main()
