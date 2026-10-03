"""Lit les dernieres mesures et conserve les alertes de maintenance."""

import json
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import tensorflow as tf


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from federated.preprocessing import FEATURES, scale_features


def configured_path(variable, default):
    value = Path(os.environ.get(variable, default)).expanduser()
    return value if value.is_absolute() else PROJECT_ROOT / value


DATA_DIR = configured_path("DATA_DIR", "data")
MODEL_PATH = configured_path("MODEL_PATH", "federated/global_model.keras")
INTERVAL = float(os.environ.get("INTERVAL", "2"))
ALERT_THRESHOLD = float(os.environ.get("ALERT_THRESHOLD", "0.5"))
FACTORIES = ("factory_1", "factory_2", "factory_3")
ALERTS_PATH = DATA_DIR / "alerts.json"
MODEL = None


def load_model():
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"Modele global absent : {MODEL_PATH}. Lancez d'abord l'entrainement federe."
        )
    return tf.keras.models.load_model(MODEL_PATH, compile=False)


def predict(sensor_values: dict) -> float:
    """Retourne la probabilite de panne pour une mesure de capteurs."""
    global MODEL
    missing = [feature for feature in FEATURES if feature not in sensor_values]
    if missing:
        raise ValueError(f"Mesures manquantes : {', '.join(missing)}")
    try:
        values = np.asarray([[float(sensor_values[key]) for key in FEATURES]], dtype=np.float32)
    except (TypeError, ValueError) as error:
        raise ValueError("Les mesures de capteurs doivent etre numeriques.") from error
    if MODEL is None:
        MODEL = load_model()
    scaled_values = scale_features(values)
    return float(MODEL.predict(scaled_values, verbose=0).reshape(-1)[0])


def write_alerts(alerts):
    ALERTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=ALERTS_PATH.parent,
            prefix=f"{ALERTS_PATH.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(alerts[-50:], temporary_file, indent=2, ensure_ascii=False)
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, ALERTS_PATH)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def read_alerts():
    if not ALERTS_PATH.is_file():
        return []
    alerts = json.loads(ALERTS_PATH.read_text(encoding="utf-8"))
    if not isinstance(alerts, list):
        raise ValueError(f"Le fichier d'alertes doit contenir une liste JSON : {ALERTS_PATH}")
    return alerts[-50:]


def run():
    global MODEL
    if INTERVAL <= 0:
        raise ValueError("INTERVAL doit etre positif")
    MODEL = load_model()
    seen_timestamps = {}
    print(f"Predicteur actif; modele : {MODEL_PATH}; seuil : {ALERT_THRESHOLD:.2f}")
    while True:
        for factory_name in FACTORIES:
            latest_path = DATA_DIR / factory_name / "latest.json"
            if not latest_path.is_file():
                continue
            try:
                measurement = json.loads(latest_path.read_text(encoding="utf-8"))
                timestamp = measurement["timestamp"]
                factory_id = measurement["factory_id"]
                if seen_timestamps.get(factory_name) == timestamp:
                    continue
                probability = predict(measurement)
                seen_timestamps[factory_name] = timestamp
            except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
                print(f"Lecture impossible pour {factory_name}: {error}")
                continue

            if probability > ALERT_THRESHOLD:
                alert = {
                    "timestamp": timestamp,
                    "factory_id": factory_id,
                    "probability": probability,
                    **{feature: float(measurement[feature]) for feature in FEATURES},
                }
                alerts = read_alerts()
                alerts.append(alert)
                write_alerts(alerts)
                print(
                    f"ALERTE {factory_id} a {timestamp} : risque de panne "
                    f"{probability:.1%} (seuil {ALERT_THRESHOLD:.1%})"
                )
        time.sleep(INTERVAL)


def main():
    try:
        run()
    except FileNotFoundError as error:
        print(error, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Arret du predicteur.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
