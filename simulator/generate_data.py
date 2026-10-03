"""Regenerate each factory history through the shared sensor stream."""

if __package__:
    from .stream_simulator import run_backfill
else:
    from stream_simulator import run_backfill


def main():
    for number in range(1, 4):
        run_backfill(
            factory_name=f"factory_{number}",
            count=12_000,
            step_seconds=60,
            reset=True,
        )


if __name__ == "__main__":
    main()
