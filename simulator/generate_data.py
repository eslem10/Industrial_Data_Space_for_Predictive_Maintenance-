"""Generate historical data through the shared stream simulator."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from .stream_simulator import run_backfill
except ImportError:
    from simulator.stream_simulator import run_backfill


def main() -> None:
    for number in range(1, 4):
        run_backfill(f"factory_{number}", count=12_000, step_seconds=60, reset=True)


if __name__ == "__main__":
    main()
