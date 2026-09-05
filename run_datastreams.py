#!/usr/bin/env python3
"""Run (fetch) Data 360 ingest data streams and poll until they finish.

Federated (zero-copy) streams need no run; file-ingest streams (the GCS leg) do — a
stream is created ACTIVE with lastRunStatus null and stays empty until it runs.
Endpoint from the d360 MCP source (DataStreamTools.runDataStream): POST /ssot/data-streams/{id}/actions/run
— the @ApiEndpoint annotation there says /run, the code builds /actions/run, and only /actions/run exists (measured 2026-09-05).

Usage:  py run_datastreams.py --org keeping-score-w6a --suffix _GCP
        py run_datastreams.py --org keeping-score-w6a --names Fct_Plays_GCP,Lahman_People_GCP
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time

API = "/services/data/v66.0/ssot/data-streams"
SF = shutil.which("sf") or sys.exit("sf CLI not found on PATH")
TERMINAL = {"SUCCESS", "SUCCEEDED", "COMPLETED", "FAILED", "FAILURE", "ERROR", "CANCELLED", "CANCELED", "NO_DATA"}


def sf_rest(alias: str, endpoint: str, method: str = "GET") -> dict | list:
    cmd = [SF, "api", "request", "rest", endpoint, "-o", alias, "--method", method]
    if method != "GET":
        cmd += ["--body", "{}", "--header", "Content-Type: application/json"]
    out = subprocess.run(cmd, capture_output=True, text=True)
    text = (out.stdout or out.stderr).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"errorCode": "NON_JSON", "message": text[:300]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--org", required=True)
    ap.add_argument("--suffix", default="_GCP", help="run every stream whose name ends with this")
    ap.add_argument("--names", default="", help="comma-separated explicit stream names (overrides --suffix)")
    ap.add_argument("--poll-seconds", type=int, default=20)
    ap.add_argument("--timeout-minutes", type=int, default=30)
    args = ap.parse_args()

    listing = sf_rest(args.org, f"{API}?limit=100")
    rows = listing if isinstance(listing, list) else listing.get("dataStreams", [])
    want = set(n for n in args.names.split(",") if n)
    targets = [s for s in rows if (s.get("name") in want) if want] if want else \
              [s for s in rows if str(s.get("name", "")).endswith(args.suffix)]
    if not targets:
        sys.exit(f"no streams matched ({'names ' + args.names if want else 'suffix ' + args.suffix})")

    # SERIAL by construction (measured 2026-09-05): seven concurrent runs on one file connection
    # -> one SUCCESS, six job-level FAILUREs with empty problem-record DLOs; the same six
    # re-run one at a time all succeeded. So: run, wait for terminal, then the next.
    failures = 0
    for s in targets:
        name, sid = s["name"], (s.get("id") or s.get("recordId"))
        resp = sf_rest(args.org, f"{API}/{sid}/actions/run", "POST")
        err = resp[0] if isinstance(resp, list) and resp and "errorCode" in resp[0] else (resp if "errorCode" in resp else None)
        print(f"  RUN   {name:32s} {'FAILED: ' + json.dumps(err)[:200] if err else 'queued'}")
        if err:
            failures += 1
            continue
        deadline = time.time() + args.timeout_minutes * 60
        status = ""
        while time.time() < deadline:
            time.sleep(args.poll_seconds)
            st = sf_rest(args.org, f"{API}/{sid}")
            status = str(st.get("lastRunStatus") or "").upper()
            if status in TERMINAL:
                break
        if status in TERMINAL:
            print(f"  DONE  {name:32s} {status}")
            failures += status not in ("SUCCESS", "SUCCEEDED", "COMPLETED")
        else:
            print(f"  TIMEOUT {name:30s} still {status or 'PENDING'} after {args.timeout_minutes} min — moving on")
            failures += 1
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
