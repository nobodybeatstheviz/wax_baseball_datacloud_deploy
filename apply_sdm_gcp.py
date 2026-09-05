#!/usr/bin/env python3
"""Build the Keeping_Score_GCP semantic model over the GCS-ingested DLOs — by INTROSPECTION.

Why a second generator instead of re-running apply_sdm_shell.py + apply_sdm.py against new
names: the original model rides an Attended_Games DMO whose fields were title-cased by the
mapping (Wax_Game_ID, Venue, Game_Date); the GCP leg rides the raw *_GCP__dll DLOs, whose
fields keep the BigQuery mart names (wax_game_id, venue_wax, game_date). And Data 360 gives
repeated field names across a model's data objects numeric suffixes (game_date1, wax_game_id2,
playerID1) in add order — predictable in theory, brittle in practice. So this script:

  1. creates the shell + the 7 data objects (same LABELS as the original, so the data-object
     apiNames match: Attended_Games, Game_Attendee, Plays, Attended_Team_Games, Lahman_People,
     Lahman_Hall_Of_Fame, HOF_Sightings),
  2. READS the model back and builds {object -> {source field name -> semantic apiName}},
  3. resolves every relationship criterion and every [Object].[field] token in the calculated
     measures/dimension through that map, then posts them.

Definitions are the ORIGINAL sdm/*.json files (one home) with one rename table for the
Attended_Games object. Idempotent — already-exists is SKIP.

Usage:  py apply_sdm_gcp.py --org keeping-score-w6a
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
API = "/services/data/v66.0/ssot/semantic/models"
DATASPACE = "default"
SF = shutil.which("sf") or sys.exit("sf CLI not found on PATH")

MODEL = {
    "apiName": "Keeping_Score_GCP",
    "label": "Keeping Score GCP",
    "description": ("The same seven governed measures as Keeping_Score, over the GCP leg: BigQuery marts "
                    "+ Lahman exported to Parquet in Google Cloud Storage and INGESTED (BigQuery's "
                    "zero-copy connector is ACCESS_CHECK in this org). Three-cloud parity column."),
    "dataspace": DATASPACE,
    "queryUnrelatedDataObjects": "Exception",
}

# label is load-bearing (object apiName = label with spaces -> underscores); order = original.
DATA_OBJECTS = [
    ("Attended_Games_GCP__dll",          "Attended Games"),
    ("Fct_Game_Attendee_GCP__dll",       "Game Attendee"),
    ("Fct_Plays_GCP__dll",               "Plays"),
    ("Fct_Attended_Team_Games_GCP__dll", "Attended Team Games"),
    ("Lahman_People_GCP__dll",           "Lahman People"),
    ("Lahman_Hall_Of_Fame_GCP__dll",     "Lahman Hall Of Fame"),
    ("Fct_Hof_Sightings_GCP__dll",       "HOF Sightings"),
]

# The original model's Attended_Games is a DMO with title-cased fields; the GCP one is the raw mart.
RENAME = {"Attended_Games": {"Wax_Game_ID": "wax_game_id", "Venue": "venue_wax", "Game_Date": "game_date"}}

# Expression fix-ups for the GCP leg: the BigQuery export types Lahman's inducted as BOOLEAN
# (Snowflake/Databricks keep the raw 'Y'/'N' text) — "Can't compare boolean and stringliteral".
EXPR_FIXUPS = [("[inducted] = 'Y'", "[inducted] = true")]


def sf_rest(alias: str, endpoint: str, method: str = "GET", payload: dict | None = None):
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


def err_of(resp) -> str | None:
    if isinstance(resp, list):
        return json.dumps(resp[0])[:300] if resp and isinstance(resp[0], dict) and "errorCode" in resp[0] else None
    if isinstance(resp, dict) and ("errorCode" in resp or "enhancedErrorType" in resp or "errorName" in resp):
        return json.dumps(resp)[:300]
    return None


def exists(err: str) -> bool:
    e = err.lower()
    # "Saving semantic entity failed: Unique ..." is the semantic-authoring spelling of
    # already-exists (measured 2026-09-05 — missing it re-posted every data object once).
    return "duplicate" in e or "already" in e or "exists" in e or "unique" in e


def post(alias, endpoint, body, what) -> bool:
    resp = sf_rest(alias, endpoint, "POST", body)
    err = err_of(resp)
    # exists() must see the FULL message — err_of truncates at 300 chars and the
    # "...Saving semantic entity failed: Unique" spelling lands right past the cut.
    if err and exists(json.dumps(resp)):
        print(f"  SKIP (exists)  {what}")
        return True
    if err:
        print(f"  FAIL           {what}: {err}")
        return False
    print(f"  OK             {what}")
    return True


# ---------------------------------------------------------------------------- introspection

def object_map(model: dict) -> dict[str, str]:
    """{label-derived name: actual data-object apiName}. Measured 2026-09-05: semantic
    definition apiNames are suffixed ORG-WIDE, not per model — the GCP model's objects came
    back as Attended_Games1, Plays1, ... because Keeping_Score already owns the bare names.
    Labels are preserved, so resolve through them."""
    out = {}
    for obj in model.get("semanticDataObjects", []):
        out[obj["label"].replace(" ", "_")] = obj["apiName"]
        out[obj["apiName"]] = obj["apiName"]
    return out


def field_map(model: dict) -> dict[str, dict[str, str]]:
    """{object apiName: {source field name: semantic field apiName}}. Keys: the DLO field
    (`dataObjectFieldName`, with and without __c), the label, and the suffix-stripped apiName
    (game_date4 -> game_date) — measured 2026-09-05 as the shape the read-back carries."""
    out: dict[str, dict[str, str]] = {}
    for obj in model.get("semanticDataObjects", []):
        m: dict[str, str] = {}
        for f in (obj.get("semanticDimensions") or []) + (obj.get("semanticMeasurements") or []):
            api = f.get("apiName")
            src = (f.get("dataObjectFieldName") or f.get("sourceFieldName") or f.get("fieldName")
                   or f.get("dataLakeFieldName") or f.get("label"))
            if src and src not in m:
                m[src] = api
                if src.endswith("__c") and src[:-3] not in m:
                    m[src[:-3]] = api
            # also index the suffix-stripped apiName (game_date1 -> game_date) as a fallback
            base = re.sub(r"\d+$", "", api or "")
            if base and base not in m:
                m[base] = api
            if api and api not in m:
                m[api] = api
        out[obj["apiName"]] = m
    return out


OMAP: dict[str, str] = {}


def obj_api(obj: str) -> str:
    if obj in OMAP:
        return OMAP[obj]
    raise SystemExit(f"object {obj} not in model (have {sorted(set(OMAP.values()))})")


def resolve(fmap, obj: str, field: str) -> str:
    field = RENAME.get(obj, {}).get(field, field)
    m = fmap.get(obj_api(obj))
    if m is None:
        raise SystemExit(f"object {obj} not in model")
    if field in m:
        return m[field]
    # case-insensitive last resort
    for k, v in m.items():
        if k.lower() == field.lower():
            return v
    raise SystemExit(f"field {field} not found on {obj}; have {sorted(m)[:20]}...")


TOKEN = re.compile(r"\[([A-Za-z0-9_]+)\]\.\[([A-Za-z0-9_]+)\]")


def resolve_expr(fmap, expr: str) -> str:
    for old, new in EXPR_FIXUPS:
        expr = expr.replace(old, new)
    return TOKEN.sub(lambda mm: f"[{obj_api(mm.group(1))}].[{resolve(fmap, mm.group(1), mm.group(2))}]", expr)


def prune_unreferenced(alias: str, base: str, model: dict) -> None:
    """Delete data objects nothing references (the duplicates a non-idempotent run left behind).
    A data object is 'used' if any relationship names it or any calc expression cites it."""
    used = set()
    for r in model.get("semanticRelationships", []):
        used.update([r.get("leftSemanticDefinitionApiName"), r.get("rightSemanticDefinitionApiName")])
    for m in model.get("semanticCalculatedMeasurements", []) + model.get("semanticCalculatedDimensions", []):
        used.update(TOKEN.findall(m.get("expression", "")) and [t[0] for t in TOKEN.findall(m.get("expression", ""))])
    for obj in model.get("semanticDataObjects", []):
        if obj["apiName"] in used:
            continue
        resp = sf_rest(alias, f"{base}/data-objects/{obj['apiName']}?dataspace={DATASPACE}", "DELETE", {})
        # a successful DELETE is 204 with an empty body -> the shim yields NON_JSON/"" = success
        err = None if (isinstance(resp, dict) and resp.get("errorCode") == "NON_JSON" and not resp.get("message")) else err_of(resp)
        print(f"  {'FAIL' if err else 'DELETED'}  unreferenced data object {obj['apiName']} ({obj['label']})" + (f": {err}" if err else ""))


# ---------------------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--org", required=True)
    ap.add_argument("--dump-fields", action="store_true", help="print the introspected field map and stop")
    ap.add_argument("--prune-unreferenced", action="store_true", help="delete data objects no relationship/measure cites, then stop")
    args = ap.parse_args()
    name = MODEL["apiName"]
    base = f"{API}/{name}"

    if args.prune_unreferenced:
        model = sf_rest(args.org, f"{base}?dataspace={DATASPACE}")
        prune_unreferenced(args.org, base, model)
        return

    print("SDM shell:")
    post(args.org, f"{API}?dataspace={DATASPACE}", MODEL, name)
    got = sf_rest(args.org, f"{base}?dataspace={DATASPACE}")
    if isinstance(got, dict) and got.get("queryUnrelatedDataObjects") != "Exception":
        upd = sf_rest(args.org, f"{base}?dataspace={DATASPACE}", "PATCH", {"queryUnrelatedDataObjects": "Exception"})
        print(f"  {'FAIL' if err_of(upd) else 'OK'}  queryUnrelatedDataObjects=Exception")

    print("data objects:")
    # idempotent by LABEL (the apiName is org-suffixed, so it can't be predicted): a label
    # already on the model is a SKIP, never a second post.
    have = {o["label"] for o in (got.get("semanticDataObjects", []) if isinstance(got, dict) else [])}
    ok = True
    for dlo, label in DATA_OBJECTS:
        if label in have:
            print(f"  SKIP (exists)  {label:22s} <- Dlo:{dlo}")
            continue
        ok &= post(args.org, f"{base}/data-objects?dataspace={DATASPACE}",
                   {"dataObjectName": dlo, "label": label, "dataObjectType": "Dlo", "shouldIncludeAllFields": True},
                   f"{label:22s} <- Dlo:{dlo}")
    if not ok:
        sys.exit("data objects failed — stopping before relationships")

    model = sf_rest(args.org, f"{base}?dataspace={DATASPACE}")
    if err_of(model):
        sys.exit(f"read-back failed: {err_of(model)}")
    fmap = field_map(model)
    OMAP.update(object_map(model))
    print("objects:", {k: v for k, v in OMAP.items() if k != v})
    if args.dump_fields:
        for obj, m in fmap.items():
            print(obj, {k: v for k, v in m.items() if k != v})
        # show the raw keys of one field so the source-name key can be pinned if needed
        first = next(iter(model.get("semanticDataObjects", [])), {})
        f0 = ((first.get("semanticDimensions") or [{}])[0])
        print("field keys:", sorted(f0.keys()))
        return

    print("relationships:")
    rels = json.loads((HERE / "sdm" / "relationships.json").read_text(encoding="utf-8"))
    for r in rels:
        body = json.loads(json.dumps(r))
        left, right = body["leftSemanticDefinitionApiName"], body["rightSemanticDefinitionApiName"]
        for c in body["criteria"]:
            c["leftSemanticFieldApiName"] = resolve(fmap, left, re.sub(r"\d+$", "", c["leftSemanticFieldApiName"]))
            c["rightSemanticFieldApiName"] = resolve(fmap, right, re.sub(r"\d+$", "", c["rightSemanticFieldApiName"]))
        body["leftSemanticDefinitionApiName"], body["rightSemanticDefinitionApiName"] = obj_api(left), obj_api(right)
        body["apiName"] = body["apiName"] + "_GCP"
        post(args.org, f"{base}/relationships?dataspace={DATASPACE}", body,
             f"{body['label']}: {body['criteria'][0]['leftSemanticFieldApiName']} = {body['criteria'][0]['rightSemanticFieldApiName']}")

    print("calculated measures:")
    for m in json.loads((HERE / "sdm" / "calc_measures.json").read_text(encoding="utf-8")):
        # apiNames are org-wide too: suffix _GCP so they don't collide with Keeping_Score's
        body = dict(m, expression=resolve_expr(fmap, m["expression"]), apiName=m["apiName"] + "_GCP")
        post(args.org, f"{base}/calculated-measurements?dataspace={DATASPACE}", body, f"{body['apiName']}: {body['expression'][:70]}")

    print("calculated dimensions:")
    for d in json.loads((HERE / "sdm" / "calc_dims.json").read_text(encoding="utf-8")):
        body = dict(d, expression=resolve_expr(fmap, d["expression"]), apiName=d["apiName"] + "_GCP")
        post(args.org, f"{base}/calculated-dimensions?dataspace={DATASPACE}", body, f"{body['apiName']}: {body['expression']}")


if __name__ == "__main__":
    main()
