"""Publish a weights file through EDC and download it through the consumer."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_PROVIDER_MANAGEMENT = "http://localhost:19193/management/v3"
DEFAULT_PROVIDER_PROTOCOL = "http://localhost:19194/protocol/2025-1"
DEFAULT_CONSUMER_MANAGEMENT = "http://localhost:29193/management/v3"
DEFAULT_OUTPUT_ROOT = Path(__file__).resolve().parent.parent / "transfers"
DEFAULT_TRACE_ROOT = Path(__file__).resolve().parent.parent / "traces"


class EDCRequestError(RuntimeError):
    """Raised when an EDC management or data request fails."""


def request_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    *,
    timeout: float,
    ignore_conflict: bool = False,
    allow_not_found: bool = False,
) -> Any:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        if ignore_conflict and isinstance(exc, HTTPError) and exc.code == 409:
            return None
        if allow_not_found and isinstance(exc, HTTPError) and exc.code == 404:
            return None
        detail = getattr(exc, "read", lambda: b"")()
        message = detail.decode("utf-8", errors="replace") or str(exc)
        raise EDCRequestError(f"{method} {url} failed: {message}") from exc

    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise EDCRequestError(f"{method} {url} returned invalid JSON") from exc


def find_offer_id(catalog: Any, asset_id: str) -> str:
    """Find the catalog policy id belonging to the requested asset."""

    matches: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            target = value.get("target", value.get("odrl:target"))
            policy_id = value.get("@id")
            if target == asset_id and isinstance(policy_id, str):
                matches.append(policy_id)
            dataset_id = value.get("@id", value.get("id"))
            policies = value.get("odrl:hasPolicy", value.get("hasPolicy"))
            if dataset_id == asset_id:
                if isinstance(policies, dict):
                    policies = [policies]
                if isinstance(policies, list):
                    for policy in policies:
                        if isinstance(policy, dict) and isinstance(
                            policy.get("@id"), str
                        ):
                            matches.append(policy["@id"])
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(catalog)
    if not matches:
        raise EDCRequestError(
            f"Catalog does not contain an offer for asset '{asset_id}'"
        )
    return matches[0]


def require_id(response: Any, label: str) -> str:
    if not isinstance(response, dict) or not isinstance(response.get("@id"), str):
        raise EDCRequestError(f"{label} response did not contain '@id': {response}")
    return response["@id"]


def wait_for_state(
    url: str,
    expected_state: str,
    *,
    timeout: float,
    poll_interval: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = request_json("GET", url, timeout=min(30.0, timeout))
        if not isinstance(response, dict):
            raise EDCRequestError(f"Unexpected response from {url}: {response}")
        state = response.get("state")
        if state == expected_state:
            return response
        if state in {"DECLINED", "TERMINATED", "ERROR"}:
            raise EDCRequestError(f"EDC process failed in state {state}: {response}")
        time.sleep(poll_interval)
    raise EDCRequestError(f"Timed out waiting for {expected_state} at {url}")


def wait_for_edr(
    url: str,
    *,
    timeout: float,
    poll_interval: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = request_json(
            "GET",
            url,
            timeout=min(30.0, timeout),
            allow_not_found=True,
        )
        if isinstance(response, dict):
            return response
        time.sleep(poll_interval)
    raise EDCRequestError(f"Timed out waiting for EDR at {url}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Publish and transfer one factory weights file through EDC."
    )
    parser.add_argument("--factory-id", required=True)
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--provider-id", default=None)
    parser.add_argument("--provider-management", default=DEFAULT_PROVIDER_MANAGEMENT)
    parser.add_argument("--provider-protocol", default=DEFAULT_PROVIDER_PROTOCOL)
    parser.add_argument("--consumer-management", default=DEFAULT_CONSUMER_MANAGEMENT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--trace-root", type=Path, default=DEFAULT_TRACE_ROOT)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--poll-interval", type=float, default=2.0)
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    if not args.weights.is_file():
        raise EDCRequestError(f"Weights file does not exist: {args.weights}")
    if args.round < 1:
        raise EDCRequestError("--round must be a positive integer")

    provider_id = args.provider_id or args.factory_id
    asset_id = f"weights-{args.factory_id}-round-{args.round}"
    policy_id = f"policy-{args.factory_id}-round-{args.round}"
    contract_definition_id = f"contract-{args.factory_id}-round-{args.round}"
    file_name = args.weights.name

    asset = {
        "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
        "@id": asset_id,
        "properties": {
            "name": f"{args.factory_id} model weights - round {args.round}",
            "contenttype": "application/json",
        },
        "dataAddress": {
            "type": "HttpData",
            "name": f"{args.factory_id} round {args.round} weights",
            "baseUrl": f"http://localhost:8000",
            "proxyPath": True,
        },
    }
    policy = {
        "@context": {
            "@vocab": "https://w3id.org/edc/v0.0.1/ns/",
            "odrl": "http://www.w3.org/ns/odrl/2/",
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
    contract_definition = {
        "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
        "@id": contract_definition_id,
        "accessPolicyId": policy_id,
        "contractPolicyId": policy_id,
        "assetsSelector": [
            {
                "operandLeft": "https://w3id.org/edc/v0.0.1/ns/id",
                "operator": "=",
                "operandRight": asset_id,
            }
        ],
    }

    provider = args.provider_management
    consumer = args.consumer_management
    request_json(
        "POST",
        f"{provider}/assets",
        asset,
        timeout=args.timeout,
        ignore_conflict=True,
    )
    request_json(
        "POST",
        f"{provider}/policydefinitions",
        policy,
        timeout=args.timeout,
        ignore_conflict=True,
    )
    request_json(
        "POST",
        f"{provider}/contractdefinitions",
        contract_definition,
        timeout=args.timeout,
        ignore_conflict=True,
    )

    catalog_request = {
        "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
        "@type": "CatalogRequest",
        "counterPartyId": provider_id,
        "counterPartyAddress": args.provider_protocol,
        "protocol": "dataspace-protocol-http:2025-1",
    }
    catalog = request_json(
        "POST", f"{consumer}/catalog/request", catalog_request, timeout=args.timeout
    )
    offer_id = find_offer_id(catalog, asset_id)

    negotiation_request = {
        "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
        "@type": "ContractRequest",
        "counterPartyId": provider_id,
        "counterPartyAddress": args.provider_protocol,
        "protocol": "dataspace-protocol-http:2025-1",
        "policy": {
            "@context": "http://www.w3.org/ns/odrl.jsonld",
            "@id": offer_id,
            "@type": "Offer",
            "assigner": provider_id,
            "target": asset_id,
        },
    }
    negotiation = request_json(
        "POST",
        f"{consumer}/contractnegotiations",
        negotiation_request,
        timeout=args.timeout,
    )
    negotiation_id = require_id(negotiation, "Contract negotiation")
    negotiation_status = wait_for_state(
        f"{consumer}/contractnegotiations/{negotiation_id}",
        "FINALIZED",
        timeout=args.timeout,
        poll_interval=args.poll_interval,
    )
    agreement_id = negotiation_status.get("contractAgreementId")
    if not isinstance(agreement_id, str):
        raise EDCRequestError("Finalized negotiation did not contain contractAgreementId")

    transfer_request = {
        "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
        "@type": "TransferRequestDto",
        "connectorId": provider_id,
        "counterPartyAddress": args.provider_protocol,
        "contractId": agreement_id,
        "protocol": "dataspace-protocol-http:2025-1",
        "transferType": "HttpData-PULL",
    }
    transfer = request_json(
        "POST", f"{consumer}/transferprocesses", transfer_request, timeout=args.timeout
    )
    transfer_id = require_id(transfer, "Transfer process")
    edr = wait_for_edr(
        f"{consumer}/edrs/{transfer_id}/dataaddress",
        timeout=args.timeout,
        poll_interval=args.poll_interval,
    )
    if not isinstance(edr, dict):
        raise EDCRequestError(f"EDR response was not an object: {edr}")
    endpoint = edr.get("endpoint")
    authorization = edr.get("authorization")
    if not isinstance(endpoint, str) or not isinstance(authorization, str):
        raise EDCRequestError(f"EDR did not contain endpoint and authorization: {edr}")

    output_path = args.output_root / args.factory_id / file_name
    output_path.parent.mkdir(parents=True, exist_ok=True)
    download_request = Request(
        f"{endpoint.rstrip('/')}/{file_name}",
        headers={"Authorization": authorization},
        method="GET",
    )
    try:
        with urlopen(download_request, timeout=args.timeout) as response:
            output_path.write_bytes(response.read())
    except (HTTPError, URLError, TimeoutError) as exc:
        raise EDCRequestError(f"Weight download failed: {exc}") from exc

    trace = {
        "factory_id": args.factory_id,
        "round": args.round,
        "asset_id": asset_id,
        "offer_id": offer_id,
        "contract_negotiation_id": negotiation_id,
        "contract_agreement_id": agreement_id,
        "transfer_process_id": transfer_id,
        "source": str(args.weights),
        "destination": str(output_path),
        "status": "TRANSFERRED",
    }
    args.trace_root.mkdir(parents=True, exist_ok=True)
    trace_path = args.trace_root / f"{args.factory_id}-round-{args.round}.json"
    trace_path.write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")
    return trace


def main() -> int:
    args = build_parser().parse_args()
    try:
        trace = run(args)
    except EDCRequestError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(trace, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
