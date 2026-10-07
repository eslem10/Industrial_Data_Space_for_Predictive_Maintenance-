<img width="1920" height="1080" alt="Design sans titre" src="https://github.com/user-attachments/assets/0a5f1a9b-8300-4dee-96d8-1c062d4af1d9" />

# Industrial Data Space for Predictive Maintenance

This project combines federated learning with Eclipse Dataspace Connectors (EDC)
and a live React dashboard for three factories.

## Local prerequisites

- Windows with Node.js installed.
- Python 3.12 (TensorFlow is run from `.venv312`).
- Java available for the EDC runtimes.

## Start the complete stack

Run each service from the repository root:

```powershell
# 1. Create the Python environment once, then install the ML dependencies.
py -3.12 -m venv .venv312
.\.venv312\Scripts\python.exe -m pip install tensorflow==2.18.0 flwr==1.19.0 numpy==1.26.4 pandas==2.2.3 scikit-learn==1.6.1 paho-mqtt==2.1.0

# 2. Generate the three factories' data.
.\.venv312\Scripts\python.exe simulator\generate_data.py

# 3. Start EDC runtimes.
.\edc-connectors\scripts\start_connectors.ps1

# 4. Start the Flower server, then one client per factory.
$env:SERVER_ADDRESS="127.0.0.1:8081"
.\.venv312\Scripts\python.exe federated\server.py
.\.venv312\Scripts\python.exe federated\client.py --factory factory_1
.\.venv312\Scripts\python.exe federated\client.py --factory factory_2
.\.venv312\Scripts\python.exe federated\client.py --factory factory_3

# 5. Start the dashboard backend and frontend in separate terminals.
Set-Location dashboard\backend; node server.js
Set-Location ..\frontend; npm run dev

# 6. Publish live MQTT measurements.
Set-Location ..\..; .\.venv312\Scripts\python.exe simulator\mqtt_simulator.py
```

The dashboard is available at `http://127.0.0.1:5173/`. Its backend health
endpoint is `http://127.0.0.1:3001/api/health`.

## Validate federated data exchange

After the EDC runtimes are ready, run:

```powershell
.\.venv312\Scripts\python.exe edc-connectors\scripts\run_federated_round.py --round 1 --continue-on-error
```

The command must report three `TRANSFERRED` factories and zero failures.
Transferred files are written below `edc-connectors/transfers/`.

## Configuration

The frontend reads `dashboard/frontend/.env` when present. Start from
`.env.example` to configure the dashboard API and local EDC management URLs.
Flower configuration is provided through environment variables used by the
scripts in `federated/`.

Generated runtime logs, Python environments, caches, EDC transfers, and
round-specific weight exports are intentionally ignored by Git. The global
model and aggregated metrics can be retained as project artifacts when
required:

- `federated/global_model.keras`
- `federated/results/metrics.json`
