"""
Workspace root runner for SIDE 1: Main Sender + Distributor.
"""
import sys
import os

if __name__ == "__main__":
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aerosar_video_distributor", "run_test.py")
    if os.path.exists(script_path):
        import runpy
        sys.argv[0] = script_path
        runpy.run_path(script_path, run_name="__main__")
    else:
        print("Error: Could not find aerosar_video_distributor/run_test.py")
