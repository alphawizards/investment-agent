# Local Dashboard Server Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Get the React trading dashboard serving locally so you can open a browser and see portfolio metrics, trades, and filters — backed by the FastAPI API.

**Architecture:** Fix the broken Vite dev entry point (`dashboard/index.html` was overwritten with build output), fix the production build's base path so FastAPI can serve it, remove JWT auth gates on local dashboard API routes, and add a single start script.

**Tech Stack:** FastAPI + Uvicorn (backend), Vite + React 18 + TypeScript + Tailwind (frontend), SQLite (local DB)

---

## Root Cause Analysis

Four things are broken:

1. **`dashboard/index.html` is corrupted** — It contains hardcoded production build asset paths (`/assets/index-BGvr5urY.js`) instead of the Vite dev entry (`/src/index.tsx`). `npm run dev` will render a blank page because Vite can't find source files to serve.

2. **Production build uses wrong base path** — `dist/index.html` references `/assets/...` (absolute root), but FastAPI mounts static files at `/dashboard/`. Browser requests go to `http://localhost:8000/assets/...` which 404s. Needs `base: '/dashboard/dist/'` in Vite config.

3. **`/api/dashboard/*` routes require JWT auth** — The dashboard router uses `Depends(get_current_user)` which requires a Bearer token. The React frontend never sends JWT tokens. These endpoints will 401.

4. **No single start command** — User must manually open two terminals (backend + Vite dev server). Needs a simple script.

---

### Task 1: Restore Vite Dev Entry Point

**Files:**
- Modify: `dashboard/index.html`

**Step 1: Overwrite dashboard/index.html with correct Vite dev entry**

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>QuantDash - Trading Strategy Dashboard</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/index.tsx"></script>
  </body>
</html>
```

This removes the hardcoded build asset references and points Vite at the TypeScript source entry point.

**Step 2: Verify Vite dev server starts without errors**

Run: `cd "C:\Users\ckr_4\01 Projects\investment-agent\dashboard" && npx vite --host 0.0.0.0 --port 3000`
Expected: Server starts on http://localhost:3000 with no compilation errors. (Kill after verifying.)

**Step 3: Commit**

```bash
git add dashboard/index.html
git commit -m "fix: restore Vite dev entry point in dashboard/index.html"
```

---

### Task 2: Fix Production Build Base Path

**Files:**
- Modify: `dashboard/vite.config.ts`

**Step 1: Add `base` option to Vite config for production builds**

In `dashboard/vite.config.ts`, add `base` to the `build` section so production assets resolve correctly when served from `/dashboard/dist/` by FastAPI:

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          charts: ['recharts'],
        },
      },
    },
  },
})
```

Note: We do NOT set `base` globally because that would break the dev server proxy. Instead, we'll fix the FastAPI mount point in Task 4.

**Step 2: Rebuild the dashboard**

Run: `cd "C:\Users\ckr_4\01 Projects\investment-agent\dashboard" && npx vite build`
Expected: Build completes, `dist/index.html` is generated with `/assets/...` paths.

**Step 3: Commit**

```bash
git add dashboard/dist/
git commit -m "build: rebuild dashboard with correct entry point"
```

---

### Task 3: Remove Auth Gate from Dashboard API Routes

**Files:**
- Modify: `backend/routers/dashboard.py:111` (get_dashboard_overview endpoint)
- Modify: `backend/routers/dashboard.py:367` (get_strategy_comparison endpoint)

The React frontend calls `/api/trades/metrics/dashboard` (no auth - works fine), but the `/api/dashboard/*` endpoints require JWT tokens the frontend never sends. Remove the auth dependency for local dev.

**Step 1: Remove `get_current_user` dependency from dashboard overview endpoint**

In `backend/routers/dashboard.py`, change:
```python
async def get_dashboard_overview(user: dict = Depends(get_current_user)) -> Dict[str, Any]:
```
to:
```python
async def get_dashboard_overview() -> Dict[str, Any]:
```

**Step 2: Remove `get_current_user` dependency from strategy comparison endpoint**

In `backend/routers/dashboard.py`, change:
```python
async def get_strategy_comparison(user: dict = Depends(get_current_user)) -> Dict[str, Any]:
```
to:
```python
async def get_strategy_comparison() -> Dict[str, Any]:
```

**Step 3: Remove unused auth import if no other endpoints use it**

Check if any other endpoints in `dashboard.py` use `get_current_user`. If not, remove the import block:
```python
# Remove these lines if unused:
try:
    from backend.auth import get_current_user
except ImportError:
    from auth import get_current_user
```

**Step 4: Verify the backend starts without import errors**

Run: `cd "C:\Users\ckr_4\01 Projects\investment-agent" && python -c "from backend.main import app; print('OK')"`
Expected: `OK`

**Step 5: Commit**

```bash
git add backend/routers/dashboard.py
git commit -m "fix: remove JWT auth from dashboard API routes for local dev"
```

---

### Task 4: Fix FastAPI Static File Mount for Production Build

**Files:**
- Modify: `backend/main.py:166-170`

The current mount serves the entire `dashboard/` directory (including `src/`, `node_modules/`, etc.) at `/dashboard`. For production, it should serve only the `dist/` folder. For local dev, the React app is served by Vite on port 3000 instead.

**Step 1: Change the static mount to serve dist/ folder**

In `backend/main.py`, change:
```python
# Mount static files for dashboard
dashboard_path = _app_dir / "dashboard"
if dashboard_path.exists():
    app.mount("/dashboard", StaticFiles(directory=str(dashboard_path), html=True), name="dashboard")
    print(f"[OK] Dashboard mounted at /dashboard from {dashboard_path}")
```

to:

```python
# Mount production dashboard build
dashboard_dist_path = _app_dir / "dashboard" / "dist"
if dashboard_dist_path.exists():
    app.mount("/dashboard", StaticFiles(directory=str(dashboard_dist_path), html=True), name="dashboard")
    print(f"[OK] Dashboard mounted at /dashboard from {dashboard_dist_path}")
else:
    print(f"[!] Dashboard dist not found at {dashboard_dist_path} - run 'npm run build' in dashboard/")
```

Now `http://localhost:8000/dashboard/` serves the production build correctly, with assets at `/dashboard/assets/...`.

**Step 2: Verify production dashboard loads**

Run: `cd "C:\Users\ckr_4\01 Projects\investment-agent" && python -m backend.main`
Then open: `http://localhost:8000/dashboard/`
Expected: The React dashboard renders (may show empty data if no trades exist - that's OK).

**Step 3: Commit**

```bash
git add backend/main.py
git commit -m "fix: serve dashboard dist/ folder instead of entire dashboard dir"
```

---

### Task 5: Add Local Dev Start Script

**Files:**
- Create: `start_dashboard.py` (project root)

**Step 1: Create a single start script that launches both servers**

```python
"""
Start local development servers.

Usage: python start_dashboard.py
- Backend API:  http://localhost:8000 (FastAPI + Uvicorn)
- Dashboard:    http://localhost:3000 (Vite dev server, proxies /api to :8000)
"""

import subprocess
import sys
import os
import signal
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
```

**Step 2: Test the start script**

Run: `cd "C:\Users\ckr_4\01 Projects\investment-agent" && python start_dashboard.py`
Expected: Both servers start. Dashboard accessible at http://localhost:3000. Ctrl+C stops both.

**Step 3: Commit**

```bash
git add start_dashboard.py
git commit -m "feat: add single start script for local dashboard development"
```

---

### Task 6: Smoke Test End-to-End

**Files:** None (verification only)

**Step 1: Start both servers**

Run: `cd "C:\Users\ckr_4\01 Projects\investment-agent" && python start_dashboard.py`

**Step 2: Verify backend health**

Run: `curl http://localhost:8000/health`
Expected: `{"status":"healthy","app":"Quant Trading Dashboard API",...}`

**Step 3: Verify API trades endpoint**

Run: `curl http://localhost:8000/api/trades`
Expected: `{"trades":[],"total":0,"page":1,...}` (or trades if DB has data)

**Step 4: Verify dashboard loads in browser**

Open: `http://localhost:3000`
Expected: React dashboard renders with header "Trading Dashboard", metric cards (showing $0.00 / 0% if no trades), and an empty trade table.

**Step 5: Verify production build route**

Open: `http://localhost:8000/dashboard/`
Expected: Same dashboard renders from the production build served by FastAPI.

**Step 6: Stop servers and commit final state**

```bash
git add -A
git commit -m "chore: verify local dashboard server working end-to-end"
```

---

## Summary of Changes

| # | File | Change | Why |
|---|------|--------|-----|
| 1 | `dashboard/index.html` | Restore Vite dev entry point | Was overwritten with build output, breaks `npm run dev` |
| 2 | `dashboard/vite.config.ts` | No change needed (base path handled by mount fix) | Dev proxy already works; production fixed via mount |
| 3 | `backend/routers/dashboard.py` | Remove JWT auth from 2 endpoints | Frontend doesn't send JWT, causes 401 |
| 4 | `backend/main.py` | Mount `dashboard/dist/` instead of `dashboard/` | Prevents serving source code; fixes asset paths |
| 5 | `start_dashboard.py` (new) | Single-command dev server launcher | No more juggling two terminals |
