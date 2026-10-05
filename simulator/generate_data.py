"""Generate historical data through the shared stream simulator."""

try:
    from .stream_simulator import run_backfill
except ImportError:
    from stream_simulator import run_backfill


def main() -> None:
    for number in range(1, 4):
        run_backfill(f"factory_{number}", count=12_000, step_seconds=60, reset=True)


if __name__ == "__main__":
    main()
