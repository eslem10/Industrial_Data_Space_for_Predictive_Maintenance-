import json
import time
import random
import paho.mqtt.client as mqtt

# ==========================================
# MQTT CONFIGURATION
# ==========================================
BROKER = "broker.emqx.io"
PORT = 1883
FACTORIES = ["F1", "F2", "F3"]


def generate_sensor_data(factory_id):

    failure = random.random() < 0.05

    if failure:
        temperature = random.gauss(90, 7)
        vibration = random.gauss(1.5, 0.3)
        pressure = random.gauss(6, 0.8)
        humidity = random.gauss(50, 6)
        energy = random.gauss(11, 1.5)
        state = "failure"

    else:
        temperature = random.gauss(65, 5)
        vibration = random.gauss(0.4, 0.12)
        pressure = random.gauss(3.5, 0.4)
        humidity = random.gauss(45, 5)
        energy = random.gauss(7, 1)
        state = "normal"

    return {
        "factory_id": factory_id,
        "temperature": round(max(0, temperature), 2),
        "vibration": round(max(0, vibration), 3),
        "pressure": round(max(0, pressure), 2),
        "humidity": round(max(0, humidity), 2),
        "energy_consumption": round(max(0, energy), 2),
        "state": state
    }


# ==========================================
# MQTT CLIENT
# ==========================================
client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="industrial-iot-simulator"
)

print("Connecting to MQTT broker...")

client.connect(BROKER, PORT, 60)

# Important pour que MQTT fonctionne correctement
client.loop_start()

print("Connected!")
print("Starting IoT simulation...")
print("------------------------------------------")


try:

    while True:

        print("Sending data from all factories...")

        # Envoyer F1, F2 et F3
        for factory in FACTORIES:

            data = generate_sensor_data(factory)

            topic = f"industrial/factory/{factory}/sensors"

            message = json.dumps(data)

            client.publish(topic, message)

            print(f"✓ {factory} sent")

        print("------------------------------------------")
        print("Waiting 30 seconds...")
        print()

        # ATTENDRE 30 SECONDES AVANT LE PROCHAIN CYCLE
        time.sleep(30)


except KeyboardInterrupt:

    print("\nSimulation stopped.")

    client.loop_stop()
    client.disconnect()