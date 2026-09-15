import json
import csv
import os
import paho.mqtt.client as mqtt


# ==========================================
# MQTT CONFIGURATION
# ==========================================

BROKER = "broker.emqx.io"
PORT = 1883

TOPIC = "industrial/factory/+/sensors"

# Project root
DATA_DIR = "../data"


# ==========================================
# Save data to CSV
# ==========================================

def save_to_csv(data):

    factory_id = data["factory_id"]

    factory_number = factory_id.replace("F", "")

    factory_dir = os.path.join(
        DATA_DIR,
        f"factory_{factory_number}"
    )

    os.makedirs(factory_dir, exist_ok=True)

    csv_file = os.path.join(
        factory_dir,
        "sensor_data.csv"
    )

    file_exists = os.path.exists(csv_file) and os.path.getsize(csv_file) > 0

    fieldnames = [
        "timestamp",
        "factory_id",
        "temperature",
        "vibration",
        "pressure",
        "humidity",
        "energy_consumption",
        "state"
    ]

    from datetime import datetime

    data["timestamp"] = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    with open(
        csv_file,
        "a",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow(data)

    print(
        f"✓ {factory_id} data saved → {csv_file}"
    )


# ==========================================
# MQTT callbacks
# ==========================================

def on_connect(client, userdata, flags, reason_code, properties):

    print("Connected to MQTT broker!")

    client.subscribe(TOPIC)

    print(f"Subscribed to: {TOPIC}")
    print("Waiting for sensor data...\n")


def on_message(client, userdata, msg):

    try:

        data = json.loads(
            msg.payload.decode()
        )

        print(f"Received from {msg.topic}")
        print(data)

        save_to_csv(data)

    except Exception as e:

        print(f"Error: {e}")


# ==========================================
# MQTT CLIENT
# ==========================================

client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="industrial-data-collector"
)

client.on_connect = on_connect
client.on_message = on_message

print("Connecting to MQTT broker...")

client.connect(
    BROKER,
    PORT,
    60
)

client.loop_forever()