import subprocess
import time
import sys
import webbrowser
import os

def main():
    print("#" * 50)
    print("HSCI: HYPER-SYMBOLIC COGNITIVE INVENTION")
    print("Launching the Verified AI Dashboard...")
    print("#" * 50)

    # 1. Start the Backend API
    print("\n[1/2] Starting Symbolic Brain Backend (FastAPI)...")
    try:
        # Use subprocess.Popen to run in background
        api_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "brain_api:app", "--host", "0.0.0.0", "--port", "8000"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT
        )
    except Exception as e:
        print(f"Error starting API: {e}")
        return

    # Give it a moment to warm up
    time.sleep(3)

    # 2. Launch the Frontend
    print("[2/2] Launching Mind-State Dashboard (UI)...")
    webbrowser.open("http://localhost:8000")

    print("\n" + "=" * 50)
    print("SYSTEM ONLINE")
    print("Dashboard Access: http://localhost:8000")
    print("Press Ctrl+C to shutdown.")
    print("=" * 50)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down cognitive core...")
        api_process.terminate()
        print("HSCI System Offline.")

if __name__ == "__main__":
    main()

