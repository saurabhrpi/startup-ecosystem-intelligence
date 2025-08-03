#!/usr/bin/env python
"""
Main entry point for Replit deployment
Runs both backend API and frontend
"""
import subprocess
import os
import sys
import time
from threading import Thread

def start_backend():
    """Start the FastAPI backend"""
    print("[BACKEND] Starting API server on port 8000...")
    env = os.environ.copy()
    env["PORT"] = "8000"
    subprocess.run([sys.executable, "run_api.py"], env=env)

def start_frontend():
    """Start the Next.js frontend"""
    print("[FRONTEND] Installing dependencies...")
    os.chdir("frontend")
    subprocess.run(["npm", "install"], check=True)
    print("[FRONTEND] Starting Next.js on port 3000...")
    subprocess.run(["npm", "run", "dev"])

def main():
    print("=" * 60)
    print("Starting Startup Ecosystem Intelligence Platform")
    print("=" * 60)
    print("[INFO] Backend API: Port 8000")
    print("[INFO] Frontend UI: Port 3000")
    print("=" * 60)
    
    # Start backend in a separate thread
    backend_thread = Thread(target=start_backend, daemon=True)
    backend_thread.start()
    
    # Give backend time to start
    print("[INFO] Waiting for backend to start...")
    time.sleep(5)
    
    # Start frontend in main thread
    try:
        start_frontend()
    except KeyboardInterrupt:
        print("\n[STOPPED] Application stopped")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    main()