#!/usr/bin/env python3
"""Check whether the local EDC file pipeline has the artifacts it needs."""

from __future__ import annotations

import argparse
import json
import socket
from pathlib import Path
from typing import Any


EDC_ROOT = Path(__file__).resolve().parents[1]
PROVIDER_JAR = (
    EDC_ROOT
    / "edc-runtime"
    / "transfer"
    / "transfer-03-consumer-pull"
    / "provider-proxy-data-plane"
    / "build"
    / "libs"
    / "connector.jar"
)
CONSUMER_JAR = (
    EDC_ROOT
    / "edc-runtime"
    / "transfer"
    / "transfer-00-prerequisites"
    / "connector"
    / "build"
    / "libs"
    / "connector.jar"
)


def tcp_available(host: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate EDC pipeline readiness.")
    parser.add_argument("--round", type=int, default=1)
    parser.add_argument("--factory", type=int, action="append", dest="factories")
    parser.add_argument("--source-dir", type=Path, default=EDC_ROOT / "weights")
    parser.add_argument("--transfer-dir", type=Path, default=EDC_ROOT / "transfers")
    parser.add_argument("--source-file-name-template", default="round_{round:03d}.npz")
    parser.add_argument("--check-connectors", action="store_true")
    parser.add_argument("--timeout", type=float, default=2.0)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    factories = args.factories or [1, 2, 3]
    source_file = args.source_file_name_template.format(round=args.round)

    checks: list[dict[str, Any]] = [
        {"name": "provider_jar", "path": str(PROVIDER_JAR), "ok": PROVIDER_JAR.is_file()},
        {"name": "consumer_jar", "path": str(CONSUMER_JAR), "ok": CONSUMER_JAR.is_file()},
    ]

    for factory in factories:
        source_path = args.source_dir / f"factory_{factory}" / source_file
        transfer_path = args.transfer_dir / f"factory_{factory}" / source_file
        checks.append({"name": f"factory_{factory}_source", "path": str(source_path), "ok": source_path.is_file()})
        checks.append({"name": f"factory_{factory}_transfer", "path": str(transfer_path), "ok": transfer_path.is_file()})

    summary_path = args.transfer_dir / f"round_{args.round:03d}_summary.json"
    checks.append({"name": "round_summary", "path": str(summary_path), "ok": summary_path.is_file()})

    if args.check_connectors:
        ports = {1: 19193, 2: 21193, 3: 23193}
        for factory in factories:
            port = ports[factory]
            checks.append({"name": f"factory_{factory}_management", "host": "localhost", "port": port, "ok": tcp_available("localhost", port, args.timeout)})
        checks.append({"name": "consumer_management", "host": "localhost", "port": 29193, "ok": tcp_available("localhost", 29193, args.timeout)})

    missing = [check for check in checks if not check["ok"]]
    report = {
        "round": args.round,
        "source_file": source_file,
        "ready": not missing,
        "checks": checks,
        "missing": missing,
    }
    print(json.dumps(report, indent=2))
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
