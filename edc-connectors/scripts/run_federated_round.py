#!/usr/bin/env python3
"""Run one EDC transfer for each factory participating in a federated round."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


EDC_ROOT = Path(__file__).resolve().parents[1]
PIPELINE = Path(__file__).with_name("run_file_pipeline.py")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the EDC file pipeline for multiple factories."
    )
    parser.add_argument(
        "--factory",
        type=int,
        action="append",
        dest="factories",
        help="Factory number to include. Repeat the option; defaults to 1, 2, and 3.",
    )
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument(
        "--provider-management-template",
        default="http://localhost:{provider_port}/management/v3",
        help="Template containing {provider_port} for each factory provider.",
    )
    parser.add_argument(
        "--provider-port-base",
        type=int,
        default=19193,
        help="Management port for factory 1; later factories use +2000.",
    )
    parser.add_argument(
        "--counter-party-address-template",
        default="http://localhost:{protocol_port}/protocol/2025-1",
        help="Template containing {protocol_port} for each provider.",
    )
    parser.add_argument(
        "--protocol-port-base",
        type=int,
        default=19194,
        help="DSP protocol port for factory 1; later factories use +2000.",
    )
    parser.add_argument(
        "--consumer-management",
        default="http://localhost:29193/management/v3",
    )
    parser.add_argument("--source-dir", type=Path, default=EDC_ROOT / "weights")
    parser.add_argument(
        "--source-file-name-template",
        default="round_{round:03d}.json",
        help="Filename template inside each factory directory.",
    )
    parser.add_argument("--source-server-port", type=int, default=8000)
    parser.add_argument(
        "--source-base-url",
        default="http://localhost:8000",
        help="Base URL providers use to fetch the weight files.",
    )
    parser.add_argument(
        "--no-source-server",
        action="store_true",
        help="Use an already-running HTTP source server.",
    )
    parser.add_argument("--output-dir", type=Path, default=EDC_ROOT / "transfers")
    parser.add_argument(
        "--trace-dir",
        type=Path,
        default=None,
        help="Directory for per-factory catalog, negotiation, and transfer traces.",
    )
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--poll-interval", type=float, default=1.5)
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Attempt remaining factories after one transfer fails.",
    )
    parser.add_argument(
        "--summary-path",
        type=Path,
        default=None,
        help="Write the round summary as JSON.",
    )
    return parser


def provider_port(factory: int, base: int) -> int:
    return base + (factory - 1) * 2000


def run_factory(args: argparse.Namespace, factory: int) -> dict[str, Any]:
    management_port = provider_port(factory, args.provider_port_base)
    protocol_port = provider_port(factory, args.protocol_port_base)
    provider_management = args.provider_management_template.format(
        provider_port=management_port,
        factory=factory,
    )
    counter_party_address = args.counter_party_address_template.format(
        protocol_port=protocol_port,
        factory=factory,
    )

    command = [
        sys.executable,
        str(PIPELINE),
        "--factory",
        str(factory),
        "--round",
        str(args.round),
        "--provider-management",
        provider_management,
        "--counter-party-address",
        counter_party_address,
        "--consumer-management",
        args.consumer_management,
        "--source-dir",
        str(args.source_dir),
        "--source-file-name",
        args.source_file_name_template.format(factory=factory, round=args.round),
        "--source-server-port",
        str(args.source_server_port),
        "--source-base-url",
        args.source_base_url,
        "--output-dir",
        str(args.output_dir),
        "--timeout",
        str(args.timeout),
        "--poll-interval",
        str(args.poll_interval),
    ]
    if args.trace_dir is not None:
        command.extend(["--trace-dir", str(args.trace_dir / f"factory_{factory}")])
    if args.no_source_server:
        command.append("--no-source-server")

    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    result: dict[str, Any] = {
        "factory": factory,
        "round": args.round,
        "provider_management": provider_management,
        "counter_party_address": counter_party_address,
        "status": "TRANSFERRED" if completed.returncode == 0 else "FAILED",
        "returncode": completed.returncode,
    }
    if completed.stdout:
        result["stdout"] = completed.stdout
    if completed.stderr:
        result["stderr"] = completed.stderr
    return result


def main() -> int:
    args = build_parser().parse_args()
    if args.round < 1:
        print("ERROR: --round must be a positive integer", file=sys.stderr)
        return 2

    factories = args.factories or [1, 2, 3]
    if any(factory < 1 for factory in factories):
        print("ERROR: factory numbers must be positive integers", file=sys.stderr)
        return 2
    if len(set(factories)) != len(factories):
        print("ERROR: each factory may be listed only once", file=sys.stderr)
        return 2

    results: list[dict[str, Any]] = []
    for factory in factories:
        print(f"[edc-round] starting factory {factory}, round {args.round}")
        result = run_factory(args, factory)
        results.append(result)
        print(f"[edc-round] factory {factory}: {result['status']}")
        if result["status"] == "FAILED" and not args.continue_on_error:
            break

    summary = {
        "round": args.round,
        "factories": factories,
        "completed": sum(result["status"] == "TRANSFERRED" for result in results),
        "failed": sum(result["status"] == "FAILED" for result in results),
        "results": results,
    }
    if args.summary_path is not None:
        args.summary_path.parent.mkdir(parents=True, exist_ok=True)
        args.summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
