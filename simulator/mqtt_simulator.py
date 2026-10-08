import json
import os
import time
import paho.mqtt.client as mqtt

from stream_simulator import generate_measurement

BROKER = os.environ.get("MQTT_BROKER_HOST", "broker.emqx.io")
PORT = int(os.environ.get("MQTT_BROKER_PORT", "1883"))

FACTORIES = ["F1", "F2", "F3"]

INTERVAL = float(os.environ.get("MQTT_INTERVAL", "30"))


client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id=os.environ.get("MQTT_CLIENT_ID", "industrial-iot-simulator")
)

print("Connecting to MQTT broker...")
client.connect(BROKER, PORT, 60)
client.loop_start()

print("Connected!")
print("Starting Industrial IoT simulation...")
print("------------------------------------------")


timestamp_index = 0

if INTERVAL <= 0:
    raise ValueError("MQTT_INTERVAL must be positive")

try:
    while True:

        print("Sending data from all factories...")

        for factory in FACTORIES:

            # Generate sensor measurements
            data = generate_measurement(factory, timestamp_index)

            # Remove the true state.
            # The ML model must predict it later.
            data.pop("state", None)

            topic = f"industrial/factory/{factory}/sensors"

            client.publish(
                topic,
                json.dumps(data)
            )

            print(f"[OK] {factory} -> {data}")

        # Next cycle
        timestamp_index += 1

        print("------------------------------------------")
        print(f"Waiting {INTERVAL} seconds...")
        print()

        time.sleep(INTERVAL)


except KeyboardInterrupt:

    print("\nSimulation stopped.")

    client.loop_stop()
    client.disconnect()
