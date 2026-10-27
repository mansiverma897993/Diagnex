"""Resilient backend launcher for local use.

The frozen BiomedCLIP towers take a couple of minutes to build on CPU, and on
Windows the build can occasionally crash the process (the OpenMP access
violation documented in the README). Running the server through this wrapper:

* Preloads the model once at startup (lifespan in main.py), so the first
  request never blocks and never surfaces a spurious "service unavailable".
* Restarts the server if it crashes before becoming healthy, and again if it
  ever dies afterwards, so the demo service stays up.

    python backend/run_backend.py            # from the repo root
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PORT = int(os.environ.get("DIAGNEX_PORT", "8000"))
HEALTH_URL = f"http://127.0.0.1:{PORT}/api/health"
MAX_STARTUP_RETRIES = 5
READY_TIMEOUT = 600  # seconds to let the CPU model build complete

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
# Local cache used by this project (D:\diagnex\.hf) when HF_HOME is unset.
_local_hf = REPO_ROOT.parent / ".hf"
if not os.environ.get("HF_HOME") and _local_hf.exists():
    os.environ["HF_HOME"] = str(_local_hf)


def healthy() -> bool:
    """True only when the API reports the model is genuinely loaded."""
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=3) as resp:
            if resp.status != 200:
                return False
            import json
            return bool(json.loads(resp.read().decode("utf-8")).get("ready"))
    except Exception:  # noqa: BLE001 - any failure means "not ready yet"
        return False


def main() -> int:
    startup_attempts = 0
    while True:
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(PORT),
        ]
        proc = subprocess.Popen(cmd, cwd=REPO_ROOT)

        deadline = time.time() + READY_TIMEOUT
        was_ready = False
        while time.time() < deadline:
            if proc.poll() is not None:
                break  # process died before signalling healthy
            if healthy():
                was_ready = True
                print(f"Diagnex backend healthy on http://localhost:{PORT}", flush=True)
                break
            time.sleep(2)

        if was_ready:
            print("watching backend process...", flush=True)
            proc.wait()
            print("backend process exited; restarting...", flush=True)
            time.sleep(2)
            continue

        startup_attempts += 1
        if startup_attempts > MAX_STARTUP_RETRIES:
            print("backend failed to become healthy after several attempts", flush=True)
            return 1
        print(
            f"backend crashed during startup (attempt {startup_attempts}); restarting...",
            flush=True,
        )
        time.sleep(3)


if __name__ == "__main__":
    raise SystemExit(main())