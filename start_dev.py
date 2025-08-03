#!/usr/bin/env python
"""
Start both backend API and frontend dev server
"""
import subprocess
import sys
import os
import time
import webbrowser
from threading import Thread

def start_backend():
    """Start the backend API server"""
    print("[BACKEND] Starting API server on http://localhost:8000")
    subprocess.run([sys.executable, "run_api.py"])

def start_frontend():
    """Start the frontend dev server"""
    os.chdir("frontend")
    print("[FRONTEND] Starting Next.js dev server on http://localhost:3000")
    subprocess.run(["npm", "run", "dev"])

def open_browser():
    """Open browser after servers start"""
    time.sleep(5)  # Wait for servers to start
    webbrowser.open("http://localhost:3000")

if __name__ == "__main__":
    print("Starting Startup Ecosystem Intelligence Platform")
    print("=" * 60)
    print("[API] Backend will run on: http://localhost:8000")
    print("[UI] Frontend will run on: http://localhost:3000")
    print("=" * 60)
    
    # Start backend in a thread
    backend_thread = Thread(target=start_backend, daemon=True)
    backend_thread.start()
    
    # Wait a bit for backend to start
    time.sleep(3)
    
    # Open browser in a thread
    browser_thread = Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # Start frontend in main thread (so Ctrl+C works)
    try:
        start_frontend()
    except KeyboardInterrupt:
        print("\n[STOPPED] Servers stopped by user")