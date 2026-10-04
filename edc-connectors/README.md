# EDC Connector File Pipeline

This folder contains the local Eclipse Dataspace Components setup for moving
factory model weight files through a provider/consumer pull flow.

## Pipeline Runner

Run the automation script after the provider and consumer connectors are up:

```powershell
python .\edc-connectors\scripts\run_file_pipeline.py --factory 1 --round 1
```

The script performs:

1. Create or reuse the provider policy.
2. Create or reuse the provider asset for `weights/factory_1/round_001.json`.
3. Create or reuse the provider contract definition.
4. Ask the consumer connector for the provider catalog.
5. Extract the live contract offer from the catalog.
6. Negotiate a contract.
7. Start an `HttpData-PULL` transfer.
8. Resolve the EDR and pull the file through the provider public endpoint.
9. Write the received file to `transfers/factory_1/round_001.json`.

By default the script also serves `edc-connectors/weights` on
`http://localhost:8000` while the transfer runs. Use `--no-source-server` if
you already have a source HTTP server running.

Useful options:

```powershell
python .\edc-connectors\scripts\run_file_pipeline.py `
  --factory 1 `
  --round 1 `
  --trace-dir .\edc-connectors\transfers\_trace\factory_1_round_001
```

The trace directory stores the catalog, negotiation, transfer, and EDR payloads
for demos and debugging.

## Démarrer les connecteurs multi-usines

Le provider doit utiliser le JAR data-plane PULL situé dans
`edc-runtime/transfer/transfer-03-consumer-pull/provider-proxy-data-plane`.
Pour démarrer les trois providers et le consumer avec leurs configurations
isolées :

```powershell
.\scripts\start_connectors.ps1
```

Les providers utilisent les ports de management `19193`, `21193` et `23193`,
et les ports DSP `19194`, `21194` et `23194`. Le consumer utilise les ports
`29193` et `29194`. Les journaux sont écrits dans `runtime-logs/`.

Cette étape ne crée pas les poids des usines 2 et 3. Les fichiers attendus sont
`weights/factory_2/round_NNN.json` et `weights/factory_3/round_NNN.json` (ou
les extensions réelles produites par le modèle), avant l'exécution du round
multi-usines.

## Federated round runner

Once provider connectors for the factories are running, one federated round can
be executed across all three providers:

```powershell
python .\edc-connectors\scripts\run_federated_round.py `
  --round 1 `
  --continue-on-error `
  --summary-path .\edc-connectors\transfers\round_001_summary.json
```

The runner invokes `run_file_pipeline.py` once per factory, using management and
DSP ports `19193/19194`, `21193/21194`, and `23193/23194` by default. Use
repeated `--factory` options to run a subset, for example
`--factory 1 --factory 3`. A non-zero exit code means at least one transfer
failed; the JSON summary preserves each subprocess output for diagnosis.

## Connector Ports

The current defaults match the checked-in local configuration:

- Provider management API: `http://localhost:19193/management/v3`
- Provider DSP endpoint: `http://localhost:19194/protocol/2025-1`
- Provider public data-plane endpoint: `http://localhost:19291/public`
- Consumer management API: `http://localhost:29193/management/v3`
