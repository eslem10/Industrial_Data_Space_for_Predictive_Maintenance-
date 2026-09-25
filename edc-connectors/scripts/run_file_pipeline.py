#!/usr/bin/env python3
"""Run the local EDC file pipeline for one factory weight round."""

from __future__ import annotations

import argparse
import functools
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


EDC_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = "dataspace-protocol-http:2025-1"
EDC_NS = "https://w3id.org/edc/v0.0.1/ns/"
DCAT_NS = "https://www.w3.org/ns/dcat#"
ODRL_NS = "http://www.w3.org/ns/odrl/2/"


class PipelineError(RuntimeError):
    pass


class QuietRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return


def log(message: str) -> None:
    print(f"[edc-pipeline] {message}")


def factory_slug(factory: int) -> str:
    return f"factory_{factory}"


def round_file_name(round_number: int) -> str:
    return f"round_{round_number:03d}.json"


def json_context() -> dict[str, str]:
    return {"@vocab": EDC_NS}


def value(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return None


def compact_list(data: Any) -> list[Any]:
    if data is None:
        return []
    if isinstance(data, list):
        return data
    return [data]


def request(
    method: str,
    url: str,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    allow_conflict: bool = False,
) -> tuple[int, bytes]:
    request_headers = dict(headers or {})
    payload = None
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url, data=payload, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        if allow_conflict and exc.code == 409:
            log(f"already exists: {url}")
            return exc.code, details.encode("utf-8")
        raise PipelineError(f"{method} {url} failed with HTTP {exc.code}: {details}") from exc
    except urllib.error.URLError as exc:
        raise PipelineError(f"{method} {url} failed: {exc.reason}") from exc


def request_json(
    method: str,
    url: str,
    body: dict[str, Any] | None = None,
    allow_conflict: bool = False,
) -> dict[str, Any]:
    status, raw = request(method, url, body=body, allow_conflict=allow_conflict)
    if not raw:
        return {"status": status}
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return {"status": status, "raw": raw.decode("utf-8", errors="replace")}
    if isinstance(parsed, dict):
        return parsed
    return {"status": status, "value": parsed}


def write_trace(trace_dir: Path | None, name: str, payload: dict[str, Any]) -> None:
    if trace_dir is None:
        return
    trace_dir.mkdir(parents=True, exist_ok=True)
    (trace_dir / name).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def start_source_server(source_dir: Path, port: int) -> ThreadingHTTPServer | None:
    handler = functools.partial(QuietRequestHandler, directory=str(source_dir))
    try:
        server = ThreadingHTTPServer(("localhost", port), handler)
    except OSError as exc:
        log(f"source server not started on port {port} ({exc}); assuming one is already running")
        return None

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    log(f"serving source files from {source_dir} at http://localhost:{port}")
    return server


def build_asset_payload(args: argparse.Namespace, source_path: str) -> dict[str, Any]:
    return {
        "@context": json_context(),
        "@id": args.asset_id,
        "properties": {
            "name": f"Factory {args.factory} model weights - round {args.round}",
            "contenttype": "application/json",
            "factory": factory_slug(args.factory),
            "round": args.round,
            "sourcePath": source_path,
        },
        "dataAddress": {
            "type": "HttpData",
            "name": f"Factory {args.factory} round {args.round} weights",
            "baseUrl": args.source_base_url.rstrip("/"),
            "proxyPath": True,
        },
    }


def build_policy_payload(policy_id: str) -> dict[str, Any]:
    return {
        "@context": {
            "@vocab": EDC_NS,
            "odrl": ODRL_NS,
        },
        "@id": policy_id,
        "policy": {
            "@context": "http://www.w3.org/ns/odrl.jsonld",
            "@type": "Set",
            "permission": [],
            "prohibition": [],
            "obligation": [],
        },
    }


def build_contract_definition_payload(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "@context": json_context(),
        "@id": args.contract_definition_id,
        "accessPolicyId": args.policy_id,
        "contractPolicyId": args.policy_id,
        "assetsSelector": [
            {
                "operandLeft": f"{EDC_NS}id",
                "operator": "=",
                "operandRight": args.asset_id,
            }
        ],
    }


def build_catalog_request(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "@context": json_context(),
        "@type": "CatalogRequest",
        "counterPartyId": args.counter_party_id,
        "counterPartyAddress": args.counter_party_address,
        "protocol": args.protocol,
    }


def extract_resource_id(payload: dict[str, Any], label: str) -> str:
    resource_id = value(payload, "@id", "id", "edc:id", f"{EDC_NS}id")
    if not isinstance(resource_id, str) or not resource_id:
        raise PipelineError(f"could not find id in {label}: {payload}")
    return resource_id


def catalog_datasets(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    datasets = value(catalog, "dcat:dataset", "dataset", f"{DCAT_NS}dataset")
    return [dataset for dataset in compact_list(datasets) if isinstance(dataset, dict)]


def dataset_id(dataset: dict[str, Any]) -> str | None:
    found = value(dataset, "@id", "id", "edc:id", f"{EDC_NS}id")
    return found if isinstance(found, str) else None


def dataset_policies(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    policies = value(dataset, "odrl:hasPolicy", "hasPolicy", f"{ODRL_NS}hasPolicy")
    return [policy for policy in compact_list(policies) if isinstance(policy, dict)]


def extract_offer_id(catalog: dict[str, Any], asset_id: str) -> str:
    datasets = catalog_datasets(catalog)
    if not datasets:
        raise PipelineError(f"catalog does not contain datasets: {catalog}")

    selected = None
    for dataset in datasets:
        if dataset_id(dataset) == asset_id:
            selected = dataset
            break

    if selected is None and len(datasets) == 1:
        selected = datasets[0]

    if selected is None:
        ids = ", ".join(dataset_id(dataset) or "<unknown>" for dataset in datasets)
        raise PipelineError(f"asset {asset_id!r} not found in catalog. Available datasets: {ids}")

    policies = dataset_policies(selected)
    if not policies:
        raise PipelineError(f"dataset {asset_id!r} has no contract policy in catalog")

    offer_id = extract_resource_id(policies[0], "catalog policy offer")
    log(f"selected catalog offer {offer_id}")
    return offer_id


def build_contract_request(args: argparse.Namespace, offer_id: str) -> dict[str, Any]:
    return {
        "@context": json_context(),
        "@type": "ContractRequest",
        "counterPartyId": args.counter_party_id,
        "counterPartyAddress": args.counter_party_address,
        "protocol": args.protocol,
        "policy": {
            "@context": "http://www.w3.org/ns/odrl.jsonld",
            "@id": offer_id,
            "@type": "Offer",
            "assigner": args.counter_party_id,
            "target": args.asset_id,
        },
    }


def build_transfer_request(args: argparse.Namespace, agreement_id: str) -> dict[str, Any]:
    return {
        "@context": json_context(),
        "@type": "TransferRequestDto",
        "connectorId": args.counter_party_id,
        "counterPartyAddress": args.counter_party_address,
        "contractId": agreement_id,
        "protocol": args.protocol,
        "transferType": "HttpData-PULL",
    }


def wait_for_negotiation(args: argparse.Namespace, negotiation_id: str) -> tuple[str, dict[str, Any]]:
    deadline = time.monotonic() + args.timeout
    url = f"{args.consumer_management}/contractnegotiations/{negotiation_id}"
    while time.monotonic() < deadline:
        payload = request_json("GET", url)
        state = str(value(payload, "state", "edc:state", f"{EDC_NS}state") or "").upper()
        if state == "FINALIZED":
            agreement_id = value(payload, "contractAgreementId", "edc:contractAgreementId", f"{EDC_NS}contractAgreementId")
            if not isinstance(agreement_id, str) or not agreement_id:
                raise PipelineError(f"negotiation finalized without contractAgreementId: {payload}")
            return agreement_id, payload
        if state in {"TERMINATED", "DECLINED", "ERROR"}:
            raise PipelineError(f"negotiation {negotiation_id} failed in state {state}: {payload}")
        log(f"negotiation {negotiation_id} state: {state or '<unknown>'}")
        time.sleep(args.poll_interval)
    raise PipelineError(f"timed out waiting for negotiation {negotiation_id}")


def wait_for_transfer_started(args: argparse.Namespace, transfer_id: str) -> dict[str, Any]:
    deadline = time.monotonic() + args.timeout
    url = f"{args.consumer_management}/transferprocesses/{transfer_id}"
    while time.monotonic() < deadline:
        payload = request_json("GET", url)
        state = str(value(payload, "state", "edc:state", f"{EDC_NS}state") or "").upper()
        if state in {"STARTED", "COMPLETED"}:
            return payload
        if state in {"TERMINATED", "ERROR"}:
            raise PipelineError(f"transfer {transfer_id} failed in state {state}: {payload}")
        log(f"transfer {transfer_id} state: {state or '<unknown>'}")
        time.sleep(args.poll_interval)
    raise PipelineError(f"timed out waiting for transfer {transfer_id}")


def wait_for_edr(args: argparse.Namespace, transfer_id: str) -> dict[str, Any]:
    deadline = time.monotonic() + args.timeout
    url = f"{args.consumer_management}/edrs/{transfer_id}/dataaddress"
    last_error = None
    while time.monotonic() < deadline:
        try:
            return request_json("GET", url)
        except PipelineError as exc:
            last_error = exc
            log(f"waiting for EDR for transfer {transfer_id}")
            time.sleep(args.poll_interval)
    raise PipelineError(f"timed out waiting for EDR for transfer {transfer_id}: {last_error}")


def pull_file(edr: dict[str, Any], source_path: str, output_path: Path) -> None:
    endpoint = value(edr, "endpoint", "edc:endpoint", f"{EDC_NS}endpoint")
    authorization = value(edr, "authorization", "edc:authorization", f"{EDC_NS}authorization")
    if not isinstance(endpoint, str) or not endpoint:
        raise PipelineError(f"EDR data address has no endpoint: {edr}")
    if not isinstance(authorization, str) or not authorization:
        raise PipelineError(f"EDR data address has no authorization token: {edr}")

    url = endpoint.rstrip("/") + "/" + source_path
    log(f"pulling file through EDR endpoint {url}")
    _, raw = request("GET", url, headers={"Authorization": authorization})

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(raw)
    log(f"wrote transferred file to {output_path}")


def configure_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local EDC file transfer pipeline.")
    parser.add_argument("--factory", type=int, default=1, help="Factory number to publish and pull.")
    parser.add_argument("--round", type=int, default=1, help="Federated learning round number.")
    parser.add_argument("--provider-management", default="http://localhost:19193/management/v3")
    parser.add_argument("--consumer-management", default="http://localhost:29193/management/v3")
    parser.add_argument("--counter-party-id", default=None)
    parser.add_argument("--counter-party-address", default="http://localhost:19194/protocol/2025-1")
    parser.add_argument("--protocol", default=DEFAULT_PROTOCOL)
    parser.add_argument("--source-base-url", default="http://localhost:8000")
    parser.add_argument("--source-dir", type=Path, default=EDC_ROOT / "weights")
    parser.add_argument("--source-server-port", type=int, default=8000)
    parser.add_argument("--no-source-server", action="store_true", help="Do not start a local HTTP file server.")
    parser.add_argument("--output-dir", type=Path, default=EDC_ROOT / "transfers")
    parser.add_argument("--policy-id", default="aPolicy")
    parser.add_argument("--asset-id", default=None)
    parser.add_argument("--contract-definition-id", default=None)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--poll-interval", type=float, default=1.5)
    parser.add_argument("--trace-dir", type=Path, default=None, help="Optional directory for response JSON traces.")
    args = parser.parse_args()

    args.counter_party_id = args.counter_party_id or f"factory-{args.factory}"
    args.asset_id = args.asset_id or f"weights-factory-{args.factory}-round-{args.round}"
    args.contract_definition_id = args.contract_definition_id or f"contract-factory-{args.factory}-round-{args.round}"
    args.provider_management = args.provider_management.rstrip("/")
    args.consumer_management = args.consumer_management.rstrip("/")
    return args


def run_pipeline(args: argparse.Namespace) -> None:
    source_path = f"{factory_slug(args.factory)}/{round_file_name(args.round)}"
    source_file = args.source_dir / source_path
    output_path = args.output_dir / source_path

    if not source_file.exists():
        raise PipelineError(f"source weight file does not exist: {source_file}")

    server = None
    if not args.no_source_server:
        server = start_source_server(args.source_dir, args.source_server_port)

    try:
        log("creating provider policy")
        request_json(
            "POST",
            f"{args.provider_management}/policydefinitions",
            build_policy_payload(args.policy_id),
            allow_conflict=True,
        )

        log("creating provider asset")
        request_json(
            "POST",
            f"{args.provider_management}/assets",
            build_asset_payload(args, source_path),
            allow_conflict=True,
        )

        log("creating provider contract definition")
        request_json(
            "POST",
            f"{args.provider_management}/contractdefinitions",
            build_contract_definition_payload(args),
            allow_conflict=True,
        )

        log("requesting consumer catalog")
        catalog = request_json("POST", f"{args.consumer_management}/catalog/request", build_catalog_request(args))
        write_trace(args.trace_dir, "catalog.json", catalog)
        offer_id = extract_offer_id(catalog, args.asset_id)

        log("starting contract negotiation")
        negotiation = request_json(
            "POST",
            f"{args.consumer_management}/contractnegotiations",
            build_contract_request(args, offer_id),
        )
        write_trace(args.trace_dir, "negotiation-created.json", negotiation)
        negotiation_id = extract_resource_id(negotiation, "contract negotiation")

        agreement_id, negotiation_final = wait_for_negotiation(args, negotiation_id)
        write_trace(args.trace_dir, "negotiation-final.json", negotiation_final)
        log(f"contract agreement finalized: {agreement_id}")

        log("starting transfer")
        transfer = request_json(
            "POST",
            f"{args.consumer_management}/transferprocesses",
            build_transfer_request(args, agreement_id),
        )
        write_trace(args.trace_dir, "transfer-created.json", transfer)
        transfer_id = extract_resource_id(transfer, "transfer process")

        transfer_state = wait_for_transfer_started(args, transfer_id)
        write_trace(args.trace_dir, "transfer-started.json", transfer_state)
        log(f"transfer process ready: {transfer_id}")

        edr = wait_for_edr(args, transfer_id)
        write_trace(args.trace_dir, "edr.json", edr)
        pull_file(edr, source_path, output_path)
    finally:
        if server is not None:
            server.shutdown()


def main() -> int:
    args = configure_args()
    try:
        run_pipeline(args)
    except PipelineError as exc:
        print(f"[edc-pipeline] error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
