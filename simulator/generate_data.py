"""Regenere les historiques via le simulateur de flux commun."""

if __package__:
    from .stream_simulator import run_backfill
else:
    from stream_simulator import run_backfill


def main():
    try:
        for number in range(1, 4):
            run_backfill(
                factory_name=f"factory_{number}",
                count=12_000,
                step_seconds=60,
                reset=True,
            )
    except KeyboardInterrupt:
        print("Arret demande; les fichiers ouverts ont ete fermes proprement.")


if __name__ == "__main__":
    main()
