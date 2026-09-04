#!/usr/bin/env python3
"""Create the Keeping_Score SDM shell and add its 7 data objects — the modeled-layer
half that W4 built interactively through the d360 MCP and never captured as a script.
This closes that gap: the whole semantic layer is now reproducible from source control.

Order in the replay:
  apply_datastreams.py  (7 streams -> 7 DLOs)
  apply_dmo.py          (Attended_Games__dlm DMO + mapping)
  apply_sdm_shell.py    (THIS: model shell + 7 data objects)   <-- must run before...
  apply_sdm.py          (relationships + calc measures + calc dims; they reference
                         the data-object apiNames this script creates)

The data-object apiName is derived from the LABEL (spaces->underscores), so the labels
in sdm/data_objects.json are load-bearing — relationships.json / calc_measures.json
reference Game_Attendee, HOF_Sightings, etc. All requests go through `sf api request
rest`; idempotent (already-exists -> SKIP).

Usage:  py apply_sdm_shell.py --org keeping-score-w6a
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
API = "/services/data/v66.0/ssot/semantic/models"
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--org", required=True, help="sf CLI org alias to deploy into")
    args = parser.parse_args()

    model = json.loads((HERE / "sdm" / "model.json").read_text(encoding="utf-8"))
    model.pop("_comment", None)
    data_objects = [d for d in json.loads((HERE / "sdm" / "data_objects.json").read_text(encoding="utf-8"))
                    if "dataObjectName" in d]
    api_name = model["apiName"]

    # 1) Create the model shell ---------------------------------------------
    print("SDM shell:")
    resp = sf_rest(args.org, f"{API}?dataspace={DATASPACE}", "POST", model)
    err = is_error(resp)
    if err and already_exists(err):
        print(f"  SKIP (exists)  {api_name}")
    elif err:
        sys.exit(f"  FAIL  {api_name}: {err}")
    else:
        print(f"  OK             {api_name}")

    # 1b) Ensure queryUnrelatedDataObjects=Exception (may be ignored on create)
    want = model.get("queryUnrelatedDataObjects")
    if want:
        got = sf_rest(args.org, f"{API}/{api_name}?dataspace={DATASPACE}")
        current = got.get("queryUnrelatedDataObjects") if isinstance(got, dict) else None
        if current != want:
            upd = sf_rest(args.org, f"{API}/{api_name}?dataspace={DATASPACE}", "PATCH",
                          {"queryUnrelatedDataObjects": want})
            uerr = is_error(upd)
            print(f"  {'FAIL' if uerr else 'OK'}  set queryUnrelatedDataObjects={want}"
                  + (f": {uerr}" if uerr else ""))
        else:
            print(f"  OK             queryUnrelatedDataObjects already {want}")

    # 2) Add the 7 data objects ---------------------------------------------
    print("data objects:")
    failures = 0
    for do in data_objects:
        body = {k: do[k] for k in ("dataObjectName", "label", "dataObjectType", "shouldIncludeAllFields")}
        resp = sf_rest(args.org, f"{API}/{api_name}/data-objects?dataspace={DATASPACE}", "POST", body)
        err = is_error(resp)
        if err and already_exists(err):
            print(f"  SKIP (exists)  {do['label']:22s} <- {do['dataObjectType']}:{do['dataObjectName']}")
        elif err:
            print(f"  FAIL           {do['label']:22s}: {err}")
            failures += 1
        else:
            print(f"  OK             {do['label']:22s} <- {do['dataObjectType']}:{do['dataObjectName']}")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
