#!/usr/bin/env python3
"""Apply the Keeping Score SDM definition (relationships + calculated measures)
to a Salesforce org — the semantic-layer half of the replay pattern.

The SDM shell + data objects are created by the d360 MCP (those endpoints work
through it); relationships MUST go raw REST — the MCP wrapper's criteria field
mangles the array (found 2026-09-01). Everything here posts via
`sf api request rest`, tolerating already-exists errors so reruns are safe.

Usage:  py apply_sdm.py --org devorg
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
MODEL = "Keeping_Score"
SF = shutil.which("sf") or sys.exit("sf CLI not found on PATH")


def sf_post(alias: str, endpoint: str, payload: dict) -> dict | list:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump(payload, fh)
        tmp = fh.name
    try:
        out = subprocess.run(
            [SF, "api", "request", "rest", endpoint, "-o", alias,
             "--method", "POST", "--body", f"@{tmp}",
             "--header", "Content-Type: application/json"],
            capture_output=True, text=True,
        )
        text = (out.stdout or out.stderr).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"errorCode": "NON_JSON", "message": text[:400]}
    finally:
        pathlib.Path(tmp).unlink(missing_ok=True)


def apply_list(alias: str, endpoint: str, items: list[dict], name_key: str) -> None:
    for item in items:
        resp = sf_post(alias, endpoint, item)
        if isinstance(resp, list) or "errorCode" in resp:
            msg = json.dumps(resp)[:300]
            status = "SKIP (exists)" if "DUPLICATE" in msg or "already" in msg.lower() else f"FAIL {msg}"
            print(f"  {status:14s} {item.get(name_key)}")
        else:
            print(f"  OK            {item.get(name_key)} -> {resp.get('id', 'created')}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--org", default="devorg")
    args = parser.parse_args()

    base = f"/services/data/v66.0/ssot/semantic/models/{MODEL}"

    print("relationships:")
    apply_list(args.org, f"{base}/relationships",
               json.loads((HERE / "sdm" / "relationships.json").read_text(encoding="utf-8")), "label")

    print("calculated measures:")
    apply_list(args.org, f"{base}/calculated-measurements",
               json.loads((HERE / "sdm" / "calc_measures.json").read_text(encoding="utf-8")), "label")

    print("calculated dimensions:")
    apply_list(args.org, f"{base}/calculated-dimensions",
               json.loads((HERE / "sdm" / "calc_dims.json").read_text(encoding="utf-8")), "label")


if __name__ == "__main__":
    main()
