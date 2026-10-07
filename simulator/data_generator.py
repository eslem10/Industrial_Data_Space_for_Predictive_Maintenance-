import random
import numpy as np


# ==========================================
# FACTORY PROFILES
# ==========================================

FACTORY_PROFILES = {

    "F1": {
        "name": "Cold Environment Factory",

        "temperature_mean": 55,
        "temperature_std": 4,

        "humidity_mean": 55,
        "humidity_std": 6,

        "pressure_mean": 3.4,
        "pressure_std": 0.35,

        "vibration_mean": 0.35,
        "vibration_std": 0.08,

        "energy_mean": 6.5,
        "energy_std": 0.8,

        "machine_age": 0.8
    },

    "F2": {
        "name": "Hot Environment Factory",

        "temperature_mean": 75,
        "temperature_std": 6,

        "humidity_mean": 65,
        "humidity_std": 7,

        "pressure_mean": 3.7,
        "pressure_std": 0.45,

        "vibration_mean": 0.45,
        "vibration_std": 0.12,

        "energy_mean": 7.5,
        "energy_std": 1.0,

        "machine_age": 1.2
    },

    "F3": {
        "name": "Old Machine Factory",

        "temperature_mean": 68,
        "temperature_std": 5,

        "humidity_mean": 48,
        "humidity_std": 5,

        "pressure_mean": 3.8,
        "pressure_std": 0.5,

        "vibration_mean": 0.70,
        "vibration_std": 0.18,

        "energy_mean": 8.5,
        "energy_std": 1.2,

        "machine_age": 2.0
    }
}


# ==========================================
# GENERATE SENSOR DATA
# ==========================================

def generate_sensor_data(factory_id, timestamp_index=0):

    profile = FACTORY_PROFILES[factory_id]

    # ------------------------------------------
    # Environmental variation
    # ------------------------------------------

    seasonal_variation = 5 * np.sin(
        timestamp_index / 500
    )

    temperature = np.random.normal(
        profile["temperature_mean"] + seasonal_variation,
        profile["temperature_std"]
    )

    humidity = np.random.normal(
        profile["humidity_mean"],
        profile["humidity_std"]
    )

    pressure = np.random.normal(
        profile["pressure_mean"],
        profile["pressure_std"]
    )

    vibration = np.random.normal(
        profile["vibration_mean"],
        profile["vibration_std"]
    )

    energy = np.random.normal(
        profile["energy_mean"],
        profile["energy_std"]
    )

    # ------------------------------------------
    # Sensor noise
    # ------------------------------------------

    temperature += np.random.normal(0, 1.5)
    vibration += np.random.normal(0, 0.03)
    pressure += np.random.normal(0, 0.08)
    humidity += np.random.normal(0, 1.5)
    energy += np.random.normal(0, 0.25)

    # ------------------------------------------
    # Failure probability
    # ------------------------------------------

    temperature_risk = max(
        0,
        (temperature - 75) / 20
    )

    vibration_risk = max(
        0,
        (vibration - 0.7) / 1.0
    )

    energy_risk = max(
        0,
        (energy - 9) / 5
    )

    pressure_risk = max(
        0,
        abs(pressure - 3.5) / 3
    )

    age_risk = profile["machine_age"] * 0.03

    failure_probability = (
        0.01
        + temperature_risk * 0.20
        + vibration_risk * 0.25
        + energy_risk * 0.10
        + pressure_risk * 0.08
        + age_risk
    )

    failure_probability = min(
        failure_probability,
        0.40
    )

    failure = random.random() < failure_probability

    # ------------------------------------------
    # Failure state
    # ------------------------------------------

    if failure:

        temperature += np.random.normal(15, 5)
        vibration += np.random.normal(0.8, 0.25)
        pressure += np.random.normal(1.5, 0.5)
        energy += np.random.normal(3, 1)

        state = "failure"

    else:

        state = "normal"

    # ------------------------------------------
    # Sensor anomaly
    # ------------------------------------------

    if random.random() < 0.02:

        sensor_to_corrupt = random.choice([
            "temperature",
            "vibration",
            "pressure",
            "humidity",
            "energy"
        ])

        if sensor_to_corrupt == "temperature":
            temperature += random.choice([-10, 10])

        elif sensor_to_corrupt == "vibration":
            vibration += random.uniform(0.2, 0.6)

        elif sensor_to_corrupt == "pressure":
            pressure += random.uniform(-1, 1)

        elif sensor_to_corrupt == "humidity":
            humidity += random.uniform(-10, 10)

        elif sensor_to_corrupt == "energy":
            energy += random.uniform(-2, 2)

    # ------------------------------------------
    # Prevent impossible values
    # ------------------------------------------

    temperature = max(0, temperature)
    vibration = max(0, vibration)
    pressure = max(0, pressure)
    humidity = min(100, max(0, humidity))
    energy = max(0, energy)

    return {
        "factory_id": factory_id,
        "temperature": round(temperature, 2),
        "vibration": round(vibration, 3),
        "pressure": round(pressure, 2),
        "humidity": round(humidity, 2),
        "energy_consumption": round(energy, 2),
        "state": state
    }