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

## Connector Ports

The current defaults match the checked-in local configuration:

- Provider management API: `http://localhost:19193/management/v3`
- Provider DSP endpoint: `http://localhost:19194/protocol/2025-1`
- Provider public data-plane endpoint: `http://localhost:19291/public`
- Consumer management API: `http://localhost:29193/management/v3`

