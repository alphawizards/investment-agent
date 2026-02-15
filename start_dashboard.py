"""
Start local development servers.

Usage: python start_dashboard.py
- Backend API:  http://localhost:8000 (FastAPI + Uvicorn)
- Dashboard:    http://localhost:3000 (Vite dev server, proxies /api to :8000)
"""

import subprocess
import sys
import os
import time

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DASHBOARD_DIR = os.path.join(ROOT_DIR, "dashboard")


def main():
    procs = []

    try:
        # Start backend
        print("[1/2] Starting backend API on http://localhost:8000 ...")
        backend = subprocess.Popen(
            [sys.executable, "-m", "backend.main"],
            cwd=ROOT_DIR,
        )
        procs.append(backend)
        time.sleep(2)

        # Start Vite dev server
        print("[2/2] Starting dashboard on http://localhost:3000 ...")
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        dashboard = subprocess.Popen(
            [npm_cmd, "run", "dev"],
            cwd=DASHBOARD_DIR,
        )
        procs.append(dashboard)

        print("\n" + "=" * 50)
        print("  Dashboard:  http://localhost:3000")
        print("  API Docs:   http://localhost:8000/docs")
        print("  Health:     http://localhost:8000/health")
        print("=" * 50)
        print("\nPress Ctrl+C to stop both servers.\n")

        # Wait for either process to exit
        while all(p.poll() is None for p in procs):
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            p.wait(timeout=5)
        print("Stopped.")


if __name__ == "__main__":
    main()
