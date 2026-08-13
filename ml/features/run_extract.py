"""Supervisor for extract.py: restart until the feature cache is complete.

torch on this machine intermittently kills the process with a Windows access
violation (exit code 0xC0000005, surfaced by the shell as 5) partway through a
long forward-pass loop. It is not a data problem - resuming from the same
position processes the same images fine - and it cannot be caught in-process,
because the fault kills the interpreter rather than raising.

extract.py checkpoints to a memmap after every batch, so the fix is simply to
run it again. This wrapper does that until it reports success or stops making
progress, and refuses to loop forever on a genuine, repeatable failure.

    python ml/features/run_extract.py --batch-size 32 --threads 4
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve()
FEATURE_DIR = Path(r"D:\diagnex\data\features")
MAX_ATTEMPTS = 60


def progress() -> tuple[int, int]:
    def read(name: str) -> int:
        p = FEATURE_DIR / f"{name}.progress"
        try:
            return int(p.read_text().strip())
        except (OSError, ValueError):
            return 0

    return read("images"), read("questions")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--threads", type=int, default=4)
    args = ap.parse_args()

    cmd = [sys.executable, str(HERE.parent / "extract.py"), "--batch-size", str(args.batch_size)]

    # Passed through the environment because extract.py must fix the OpenMP
    # thread count before importing torch; calling torch.set_num_threads()
    # afterwards and then building the ViT faults the process.
    import os

    env = dict(os.environ, DIAGNEX_THREADS=str(args.threads))

    last = progress()
    stalled = 0

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"[run] attempt {attempt}: {' '.join(cmd[1:])}", flush=True)
        result = subprocess.run(cmd, env=env)
        if result.returncode == 0:
            print("[run] extraction complete", flush=True)
            return 0

        now = progress()
        moved = now[0] > last[0] or now[1] > last[1]
        print(
            f"[run] exit {result.returncode} (0x{result.returncode & 0xFFFFFFFF:X}); "
            f"progress images={now[0]} questions={now[1]}"
            f"{' - advancing' if moved else ' - NO PROGRESS'}",
            flush=True,
        )

        # A crash that makes no headway twice running is a real bug, not the
        # flaky allocator; stop rather than spin.
        stalled = 0 if moved else stalled + 1
        if stalled >= 2:
            print("[run] no progress across two attempts; giving up", flush=True)
            return 1
        last = now
        time.sleep(2)

    print(f"[run] hit {MAX_ATTEMPTS} attempts without finishing", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
