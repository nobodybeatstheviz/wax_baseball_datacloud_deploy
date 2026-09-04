#!/usr/bin/env python3
"""Create the Attended_Games__dlm DMO and its DLO->DMO mapping — the ONE modeled
object the Keeping_Score SDM references as a Dmo (the other six ride their DLOs).

Why this exists: in devorg Attended_Games pre-existed as a DMO from an earlier
federation, so it was never in the deploy repo. A fresh org needs it rebuilt.
Its SDM measures reference title-cased fields ([Attended_Games].[Wax_Game_ID],
[Venue], [Game_Date]) that only a DMO produces, and the source column 'Date' is
renamed to 'Game_Date' in the mapping — so it must be a DMO, not a DLO shortcut.

Order: run AFTER apply_datastreams.py (needs the Attended_Games__dll DLO to exist)
and BEFORE apply_sdm_shell.py (the SDM adds Attended_Games__dlm as a data object).

All requests go through `sf api request rest`, which signs with the CLI's own auth
for the target alias. Idempotent: already-exists is treated as SKIP.

Usage:  py apply_dmo.py --org keeping-score-w6a
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
API = "/services/data/v66.0/ssot"
DATASPACE = "default"
SF = shutil.which("sf") or sys.exit("sf CLI not found on PATH")


def sf_rest(alias: str, endpoint: str, method: str = "GET", payload: dict | None = None) -> dict | list:
    cmd = [SF, "api", "request", "rest", endpoint, "-o", alias, "--method", method]
    tmp = None
    if payload is not None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
            json.dump(payload, fh)
            tmp = fh.name
        cmd += ["--body", f"@{tmp}", "--header", "Content-Type: application/json"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True)
        text = (out.stdout or out.stderr).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"errorCode": "NON_JSON", "message": text[:400]}
    finally:
        if tmp:
            pathlib.Path(tmp).unlink(missing_ok=True)


def is_error(resp: dict | list) -> str | None:
    """Return an error string if the response is an error, else None."""
    if isinstance(resp, list):
        if resp and isinstance(resp[0], dict) and "errorCode" in resp[0]:
            return json.dumps(resp[0])[:300]
        return None
    if isinstance(resp, dict) and "errorCode" in resp:
        return json.dumps(resp)[:300]
    return None


def already_exists(err: str) -> bool:
    e = err.lower()
    return "duplicate" in e or "already" in e or "exists" in e


def dlo_field_names(alias: str, dlo_name: str) -> dict[str, str]:
    """Map base field name (upper, no __c) -> actual DLO field developer name.

    Response shape (verified against devorg 2026-09-04):
      { "dataLakeObjects": [ { "dataLakeFieldInfoRepresentation": [
          { "name": "runs_on_play__c", "label": ..., "dataType": ... }, ... ] } ] }
    Field developer names carry a __c suffix and preserve source-column casing.
    """
    resp = sf_rest(alias, f"{API}/data-lake-objects/{dlo_name}?dataspace={DATASPACE}")
    err = is_error(resp)
    if err:
        sys.exit(f"cannot read DLO {dlo_name}: {err}\n"
                 f"(run apply_datastreams.py first so the DLO exists)")
    dlos = resp.get("dataLakeObjects", []) if isinstance(resp, dict) else []
    if not dlos:
        sys.exit(f"DLO {dlo_name} returned no dataLakeObjects — not created yet? {json.dumps(resp)[:200]}")
    fields = dlos[0].get("dataLakeFieldInfoRepresentation", [])
    out = {}
    for f in fields:
        dev = f.get("name") or f.get("developerName") or f.get("fieldName")
        if not dev:
            continue
        base = dev[:-3] if dev.endswith("__c") else dev
        out[base.upper()] = dev
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--org", required=True, help="sf CLI org alias to deploy into")
    args = parser.parse_args()

    dmo_spec = json.loads((HERE / "sdm" / "attended_games_dmo.json").read_text(encoding="utf-8"))
    dmo_spec.pop("_comment", None)
    map_spec = json.loads((HERE / "sdm" / "attended_games_mapping.json").read_text(encoding="utf-8"))
    map_spec.pop("_comment", None)

    # 1) Create the DMO ------------------------------------------------------
    print("DMO create:")
    resp = sf_rest(args.org, f"{API}/data-model-objects?dataspace={DATASPACE}", "POST", dmo_spec)
    err = is_error(resp)
    if err and already_exists(err):
        print(f"  SKIP (exists)  {dmo_spec['name']}__dlm")
    elif err:
        sys.exit(f"  FAIL  {dmo_spec['name']}__dlm: {err}")
    else:
        print(f"  OK             {dmo_spec['name']}__dlm")

    # 2) Resolve DLO field casing from the live DLO --------------------------
    src_dlo = map_spec["sourceDlo"]
    tgt_dmo = map_spec["targetDmo"]
    dlo_fields = dlo_field_names(args.org, src_dlo)

    field_mapping = []
    for pair in map_spec["fieldMapping"]:
        src_dev = dlo_fields.get(pair["source"].upper())
        if not src_dev:
            sys.exit(f"  source field '{pair['source']}' not found on DLO {src_dlo}; "
                     f"DLO has: {sorted(dlo_fields)}")
        field_mapping.append({
            "sourceFieldDeveloperName": src_dev,
            "targetFieldDeveloperName": f"{pair['target']}__c",
        })

    # 3) Create the DLO->DMO mapping ----------------------------------------
    print("DMO mapping:")
    body = {
        "sourceEntityDeveloperName": src_dlo,
        "targetEntityDeveloperName": tgt_dmo,
        "fieldMapping": field_mapping,
    }
    resp = sf_rest(args.org, f"{API}/data-model-object-mappings?dataspace={DATASPACE}", "POST", body)
    err = is_error(resp)
    if err and already_exists(err):
        print(f"  SKIP (exists)  {src_dlo} -> {tgt_dmo} ({len(field_mapping)} fields)")
    elif err:
        sys.exit(f"  FAIL  {src_dlo} -> {tgt_dmo}: {err}")
    else:
        print(f"  OK             {src_dlo} -> {tgt_dmo} ({len(field_mapping)} fields)")


if __name__ == "__main__":
    main()
