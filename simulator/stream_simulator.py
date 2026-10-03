"""Simulate and store one sensor stream for one factory."""

import argparse
import csv
import json
import math
import os
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR_VALUE = os.environ.get("DATA_DIR", "data")
DATA_DIR = Path(DATA_DIR_VALUE).expanduser()
if not DATA_DIR.is_absolute():
    DATA_DIR = PROJECT_ROOT / DATA_DIR

INTERVAL = float(os.environ.get("INTERVAL", "2"))
MQTT_HOST = os.environ.get("MQTT_HOST")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
BACKFILL_START = datetime.fromisoformat("2026-01-01T00:00:00")
SAMPLES_FOR_CALIBRATION = 120_000
FAILURE_RATE = 0.06
SEED_BASE = 20261003

PROFILES = {
    "F1": {
        "temperature": (55.0, 7.0),
        "vibration": (0.35, 0.13),
        "pressure": (3.4, 0.55),
        "humidity": (55.0, 8.0),
        "energy_consumption": (6.5, 1.2),
    },
    "F2": {
        "temperature": (75.0, 8.0),
        "vibration": (0.45, 0.16),
        "pressure": (3.7, 0.65),
        "humidity": (65.0, 9.0),
        "energy_consumption": (7.5, 1.4),
    },
    "F3": {
        "temperature": (68.0, 8.0),
        "vibration": (0.70, 0.20),
        "pressure": (3.8, 0.70),
        "humidity": (48.0, 7.0),
        "energy_consumption": (8.5, 1.6),
    },
}
FEATURES = list(PROFILES["F1"])
RISK_FEATURES = ["temperature", "vibration", "pressure", "energy_consumption"]
RISK_WEIGHTS = np.array([0.30, 0.30, 0.20, 0.20], dtype=np.float64)
CSV_FIELDS = ["timestamp", "factory_id", *FEATURES, "state"]


def factory_number(factory_name):
    if factory_name not in {"factory_1", "factory_2", "factory_3"}:
        raise ValueError("Usine attendue : factory_1, factory_2 ou factory_3")
    return int(factory_name[-1])


def factory_id_for(factory_name):
    return f"F{factory_number(factory_name)}"


def factory_paths(factory_name):
    folder = DATA_DIR / factory_name
    return folder / "sensor_data.csv", folder / "latest.json"


def sigmoid(values):
    values = np.clip(values, -60, 60)
    return 1.0 / (1.0 + np.exp(-values))


def calibrate_intercept(factory_id):
    """Calibre un seuil fixe pour viser environ 6 % de pannes."""
    profile = PROFILES[factory_id]
    rng = np.random.default_rng(SEED_BASE + int(factory_id[-1]) * 100)
    indices = np.arange(SAMPLES_FOR_CALIBRATION, dtype=np.float64)
    standardized = []
    for feature in RISK_FEATURES:
        mean, scale = profile[feature]
        drift = 1.2 * np.sin(indices / 900.0 + int(factory_id[-1]))
        shared_variation = rng.normal(0.0, 0.18, len(indices))
        sensor_variation = rng.normal(0.0, 1.0, len(indices))
        standardized.append(sensor_variation + shared_variation + drift / scale)
    risk = 3.0 * np.sum(np.vstack(standardized).T * RISK_WEIGHTS, axis=1)
    risk += rng.normal(0.0, 0.75, len(indices))

    low, high = -20.0, 5.0
    for _ in range(70):
        middle = (low + high) / 2.0
        if float(np.mean(sigmoid(middle + risk))) < FAILURE_RATE:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


FAILURE_INTERCEPTS = {factory_id: calibrate_intercept(factory_id) for factory_id in PROFILES}


def generate_measurement(factory_name, timestamp, rng, sample_index):
    """Genere une mesure et son etat a l'instant donne."""
    factory_id = factory_id_for(factory_name)
    profile = PROFILES[factory_id]
    values = {}
    standardized = []
    drift = 1.2 * math.sin(sample_index / 900.0 + factory_number(factory_name))

    for feature, (mean, scale) in profile.items():
        shared_variation = rng.normal(0.0, 0.18)
        measurement = rng.normal(mean + drift, scale) + shared_variation * scale
        values[feature] = measurement
        if feature in RISK_FEATURES:
            standardized.append((measurement - mean) / scale)

    risk = 3.0 * float(np.dot(standardized, RISK_WEIGHTS)) + rng.normal(0.0, 0.75)
    failure_probability = float(sigmoid(FAILURE_INTERCEPTS[factory_id] + risk))
    state = "failure" if rng.random() < failure_probability else "normal"

    for feature, (_, scale) in profile.items():
        if rng.random() < 0.01:
            values[feature] += rng.normal(0.0, 2.5 * scale)

    result = {
        "timestamp": timestamp.isoformat(timespec="seconds"),
        "factory_id": factory_id,
        **{feature: round(max(float(values[feature]), 0.0), 3) for feature in FEATURES},
        "state": state,
    }
    return result


def write_latest(latest_path, measurement):
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=latest_path.parent,
            prefix=f"{latest_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(measurement, temporary_file, ensure_ascii=False)
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, latest_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def create_mqtt_publisher(factory_name):
    if not MQTT_HOST:
        return None
    try:
        import paho.mqtt.client as mqtt
    except ImportError as error:
        raise RuntimeError("MQTT_HOST est defini, mais paho-mqtt n'est pas installe.") from error

    publisher = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    publisher.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    publisher.loop_start()
    print(f"Publication MQTT active : {MQTT_HOST}:{MQTT_PORT}")
    return publisher


def store_measurement(factory_name, measurement, csv_writer, csv_file, latest_path, publisher=None, update_latest=True):
    csv_writer.writerow(measurement)
    csv_file.flush()
    if update_latest:
        write_latest(latest_path, measurement)
    if publisher is not None:
        topic = f"industrial/{factory_name}/sensors"
        publisher.publish(topic, json.dumps(measurement, ensure_ascii=False))


def open_csv(csv_path, reset=False):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if reset and csv_path.exists():
        print(f"--reset : le contenu suivant sera ecrase : {csv_path}")
    mode = "w" if reset else "a"
    csv_file = csv_path.open(mode, newline="", encoding="utf-8")
    writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
    if reset or csv_file.tell() == 0:
        writer.writeheader()
        csv_file.flush()
    return csv_file, writer


def run_backfill(factory_name, count, step_seconds=60, reset=False):
    if count < 1:
        raise ValueError("Le nombre de mesures --backfill doit etre positif")
    if step_seconds < 1:
        raise ValueError("--step-seconds doit etre positif")

    csv_path, latest_path = factory_paths(factory_name)
    rng = np.random.default_rng(SEED_BASE + factory_number(factory_name))
    publisher = create_mqtt_publisher(factory_name)
    csv_file, writer = open_csv(csv_path, reset=reset)
    last_measurement = None
    try:
        for index in range(count):
            timestamp = BACKFILL_START + timedelta(seconds=index * step_seconds)
            measurement = generate_measurement(factory_name, timestamp, rng, index)
            last_measurement = measurement
            store_measurement(
                factory_name,
                measurement,
                writer,
                csv_file,
                latest_path,
                publisher,
                update_latest=False,
            )
    finally:
        csv_file.close()
        if last_measurement is not None:
            write_latest(latest_path, last_measurement)
        if publisher is not None:
            publisher.loop_stop()
            publisher.disconnect()
    print(f"{factory_name}: {count} mesures ajoutees dans {csv_path}; derniere mesure : {latest_path}")


def run_realtime(factory_name, reset=False):
    if INTERVAL <= 0:
        raise ValueError("INTERVAL doit etre positif")

    csv_path, latest_path = factory_paths(factory_name)
    rng = np.random.default_rng(SEED_BASE + factory_number(factory_name))
    publisher = create_mqtt_publisher(factory_name)
    csv_file, writer = open_csv(csv_path, reset=reset)
    index = 0
    try:
        while True:
            measurement = generate_measurement(
                factory_name,
                datetime.now().astimezone(),
                rng,
                index,
            )
            store_measurement(factory_name, measurement, writer, csv_file, latest_path, publisher)
            print(f"[{measurement['timestamp']}] {factory_name}: {measurement['state']}")
            index += 1
            time.sleep(INTERVAL)
    finally:
        csv_file.flush()
        csv_file.close()
        if publisher is not None:
            publisher.loop_stop()
            publisher.disconnect()


def main():
    parser = argparse.ArgumentParser(description="Simule le flux de capteurs d'une usine.")
    parser.add_argument("factory", choices=("factory_1", "factory_2", "factory_3"))
    parser.add_argument("--backfill", type=int, help="Nombre de mesures historiques a emettre sans attente")
    parser.add_argument("--step-seconds", type=int, default=60, help="Intervalle entre horodatages historiques")
    parser.add_argument("--reset", action="store_true", help="Vider le CSV avant d'ecrire, avec avertissement affiche")
    arguments = parser.parse_args()

    try:
        if arguments.backfill is None:
            run_realtime(arguments.factory, reset=arguments.reset)
        else:
            run_backfill(
                arguments.factory,
                count=arguments.backfill,
                step_seconds=arguments.step_seconds,
                reset=arguments.reset,
            )
    except KeyboardInterrupt:
        print("Arret demande; CSV et fichiers ouverts ont ete fermes proprement.")
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
