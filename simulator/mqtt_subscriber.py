import json
import csv
import os
from datetime import datetime
import paho.mqtt.client as mqtt

BROKER = "broker.emqx.io"
PORT = 1883
TOPIC = "industrial/factory/+/sensors"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")


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

    data["timestamp"] = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    file_exists = os.path.exists(csv_file)

    with open(csv_file, "a", newline="", encoding="utf-8") as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow(data)

    print(f"✓ SAVED → {csv_file}")


def on_connect(client, userdata, flags, reason_code, properties):

    print("Connected to MQTT broker!")
    print("Connection code:", reason_code)

    result = client.subscribe(TOPIC)

    print("Subscribe result:", result)
    print("Subscribed to:", TOPIC)
    print("Waiting for sensor data...\n")


def on_message(client, userdata, msg):

    print("\n==============================")
    print("📩 MESSAGE RECEIVED")
    print("Topic:", msg.topic)
    print("Payload:", msg.payload.decode())
    print("==============================")

    try:

        data = json.loads(msg.payload.decode())

        save_to_csv(data)

    except Exception as e:

        print("❌ Error:", e)


client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="industrial-data-collector-test"
)

client.on_connect = on_connect
client.on_message = on_message

print("Connecting to MQTT broker...")

client.connect(BROKER, PORT, 60)

client.loop_forever()