#!/usr/bin/env python3
"""Apply the generated data-stream payloads to a Salesforce org — the replayable half.

All requests go through `sf api request rest`, which signs with the CLI's own
auth for the target alias — a raw Bearer of the CLI session token gets
INVALID_AUTH_HEADER from the ssot endpoints (learned here 2026-09-01).
Idempotent: streams whose name already exists in the org are skipped.

Usage:  py apply_datastreams.py --org devorg
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys

PAYLOAD_DIR = pathlib.Path(__file__).resolve().parent / "payloads"
API = "/services/data/v66.0/ssot/data-streams"
SF = shutil.which("sf") or sys.exit("sf CLI not found on PATH")


def sf_rest(alias: str, endpoint: str, method: str = "GET", body_file: pathlib.Path | None = None) -> dict | list:
    cmd = [SF, "api", "request", "rest", endpoint, "-o", alias, "--method", method]
    if body_file is not None:
        cmd += ["--body", f"@{body_file}", "--header", "Content-Type: application/json"]
    out = subprocess.run(cmd, capture_output=True, text=True)
    text = out.stdout.strip()
    if out.returncode != 0 and not text:
        raise RuntimeError(out.stderr.strip()[:400])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise RuntimeError(f"non-JSON response: {text[:400]}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--org", default="devorg", help="sf CLI org alias to deploy into")
    parser.add_argument("--dir", default="", help="payload subfolder (e.g. gcs for the Parquet-ingest streams); default = the federated streams")
    args = parser.parse_args()

    payloads = sorted((PAYLOAD_DIR / args.dir).glob("*.json"))
    if not payloads:
        sys.exit("No payloads found — run generate_payloads.py first.")

    listing = sf_rest(args.org, f"{API}?limit=50")
    rows = listing if isinstance(listing, list) else listing.get("dataStreams", [])
    existing = {ds.get("name") for ds in rows if isinstance(ds, dict)}
    print(f"org {args.org}: {len(existing)} existing streams")

    failures = 0
    for path in payloads:
        name = json.loads(path.read_text(encoding="utf-8"))["name"]
        if name in existing:
            print(f"  SKIP  {name} (exists)")
            continue
        try:
            resp = sf_rest(args.org, API, method="POST", body_file=path)
        except RuntimeError as exc:
            print(f"  FAIL  {name}: {exc}")
            failures += 1
            continue
        if isinstance(resp, list) or "errorCode" in resp:
            print(f"  FAIL  {name}: {json.dumps(resp)[:400]}")
            failures += 1
        else:
            print(f"  OK    {name} -> {resp.get('recordId', 'created')}")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
