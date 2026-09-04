#!/usr/bin/env python3
"""Create Data 360 source connections HEADLESSLY — no GUI.

Proven 2026-09-04: POST /ssot/connections creates a connection using only the
CLI's Data 360 token (a dummy Snowflake connection round-tripped clean). So the
"GUI floor" in the old runbook is not a floor — this script replaces Step 0.

Credentials are read from their standard local homes at RUNTIME and never printed:
  - Snowflake : ~/.snowflake/connections.toml (conn wax_baseball_key) + the .p8 key
  - Databricks: ~/.databrickscfg (profile wax_baseball)
  - BigQuery  : a service-account JSON key path passed via --bq-key

After create, each connection is functionally probed by listing its database-schemas
through the connection — if that returns real warehouse metadata, the connection works
AND (for zero-copy) the region is compatible. That probe is the measurement.

Usage:
  py apply_connections.py --org keeping-score-w6a --engine snowflake
  py apply_connections.py --org keeping-score-w6a --engine databricks
  py apply_connections.py --org keeping-score-w6a --engine bigquery --bq-key C:/path/to/sa.json
  py apply_connections.py --org keeping-score-w6a --engine all --bq-key ...
"""

from __future__ import annotations

import argparse
import configparser
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

HOME = pathlib.Path.home()
API = "/services/data/v66.0/ssot"
DATASPACE = "default"
SF = shutil.which("sf") or sys.exit("sf CLI not found on PATH")

# --- non-secret connection coordinates (secrets are read from disk at runtime) ---
SNOWFLAKE = {
    "label": "Snowflake_Baseball", "name": "Snowflake_Baseball",
    "accountUrl": "https://OSWNWTM-YLC58210.snowflakecomputing.com",
    "region": "us-east-1", "warehouse": "WAX_WH", "user": "WAX",
    "keyfile": HOME / ".snowflake" / "wax_rsa_key.p8",
    "probe_db": "BASEBALL",
}
DATABRICKS = {
    "label": "Databricks_Baseball", "name": "Databricks_Baseball",
    # D360 wants the BARE HOSTNAME here (not a jdbc: URL) — it builds the JDBC URL
    # internally from hostname + httpPath. A full jdbc:spark:// URL -> CONNECTION_NOT_ESTABLISHED.
    # Also: the SQL warehouse must be RUNNING when the connection is created/tested.
    "jdbc_url": "dbc-9a4434eb-8c0f.cloud.databricks.com",
    "httpPath": "/sql/1.0/warehouses/873a5fb5d84620c1",
    "profile": "wax_baseball",
    "probe_db": "lahman_baseball",  # Unity Catalog CATALOG (D360 calls it 'database')
}


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


def is_error(resp):
    if isinstance(resp, list):
        return json.dumps(resp[0])[:300] if resp and isinstance(resp[0], dict) and "errorCode" in resp[0] else None
    if isinstance(resp, dict) and "errorCode" in resp:
        return json.dumps(resp)[:300]
    return None


def cparam(name, value):
    return {"paramName": name, "value": value}


def create_and_probe(alias: str, body: dict, probe_db: str | None) -> None:
    label = body["label"]
    print(f"\n=== {label} ({body['connectorType']}) ===")
    existing = sf_rest(alias, f"{API}/connections?connectorType={body['connectorType']}")
    conns = existing.get("connections", []) if isinstance(existing, dict) else []
    match = next((c for c in conns if c.get("name") == body["name"]), None)
    if match:
        print(f"  connection exists (id {match.get('id')}) — SKIP create")
        conn_id = match.get("id")
    else:
        resp = sf_rest(alias, f"{API}/connections?dataspace={DATASPACE}", "POST", body)
        err = is_error(resp)
        if err:
            print(f"  CREATE FAILED: {err}")
            return
        conn_id = resp.get("id")
        print(f"  created (id {conn_id})")

    # functional probe: list database-schemas THROUGH the connection (POST, per MCP source).
    # If this returns real schemas, the connection reaches the source AND (zero-copy) the region works.
    if not probe_db:
        print("  (no probe_db set — skipping functional probe)")
        return
    probe_body = {"advancedAttributes": {"DATABASE": probe_db}}  # connector attr name is uppercase
    probe = sf_rest(alias, f"{API}/connections/{conn_id}/database-schemas?dataspace={DATASPACE}",
                    "POST", probe_body)
    err = is_error(probe)
    if err:
        print(f"  PROBE (schemas in '{probe_db}') FAILED: {err}")
        print("  -> connection stored but cannot reach the source (creds/region/access).")
        return
    payload = probe if isinstance(probe, dict) else {}
    schemas = payload.get("databaseSchemas") or payload.get("schemas") or payload.get("items") or []
    print(f"  PROBE OK — reached '{probe_db}', {len(schemas)} schema(s) returned:")
    for s in schemas[:10]:
        name = s if isinstance(s, str) else (s.get("name") or s.get("label") or s)
        print(f"     - {name}")


def _pem_body(pem: str) -> str:
    """Strip PEM armor + whitespace -> base64 DER body only.
    Data 360 rejects the -----BEGIN----- header ('Illegal base64 character 2d')."""
    lines = [ln for ln in pem.splitlines() if ln and not ln.startswith("-----")]
    return "".join(lines).strip()


def build_snowflake() -> dict:
    key = _pem_body(pathlib.Path(SNOWFLAKE["keyfile"]).read_text(encoding="utf-8"))
    return {
        "connectorType": "SNOWFLAKE", "label": SNOWFLAKE["label"], "name": SNOWFLAKE["name"],
        "method": "Ingress",
        "credentials": [cparam("authenticationOption", "KeyPair"),
                        cparam("user", SNOWFLAKE["user"]),
                        cparam("privateKey", key)],
        "parameters": [cparam("hasPrivateNetworkRoute", "false"),
                       cparam("accountUrl", SNOWFLAKE["accountUrl"]),
                       cparam("region", SNOWFLAKE["region"]),
                       cparam("warehouse", SNOWFLAKE["warehouse"])],
    }


def build_databricks() -> dict:
    cfg = configparser.ConfigParser()
    cfg.read(HOME / ".databrickscfg")
    token = cfg[DATABRICKS["profile"]]["token"]
    return {
        "connectorType": "Databricks", "label": DATABRICKS["label"], "name": DATABRICKS["name"],
        "method": "Ingress",
        "credentials": [cparam("credentialType", "passwordBasedAuthentication"),
                        cparam("user", "token"),
                        cparam("password", token)],
        "parameters": [cparam("hasPrivateNetworkRoute", "false"),
                       cparam("jdbc_connection_url", DATABRICKS["jdbc_url"]),
                       cparam("httpPath", DATABRICKS["httpPath"])],
    }


def build_bigquery(bq_key_path: str, gcs_bucket: str = "gs://wax-ss49-spec-sheets") -> dict:
    """KeyPair (service-account) path — no externalId, so no GUI handshake. NOTE: blocked in
    this org by the BigQuery connector's ACCESS_CHECK entitlement (measured 2026-09-04: the
    key is valid — direct query works — but D360 returns 'Failed to connect'). This body shape
    is correct and ready for when/if the connector is entitled. The SA needs storage access to
    gcs_bucket (roles/storage.objectAdmin) for BQ unload."""
    key = json.loads(pathlib.Path(bq_key_path).read_text(encoding="utf-8"))
    return {
        "connectorType": "BIGQUERY", "label": "BigQuery_Baseball", "name": "BigQuery_Baseball",
        "method": "Ingress",
        "credentials": [cparam("authenticationOption", "KeyPair"),
                        cparam("serviceAccountEmail", key["client_email"]),
                        cparam("privateKey", _pem_body(key["private_key"]))],
        "parameters": [cparam("hasPrivateNetworkRoute", "false"),
                       cparam("projectId", key.get("project_id", "augmented-world-262319")),
                       cparam("gcsBucketAbsolutePath", gcs_bucket)],
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--org", required=True)
    p.add_argument("--engine", choices=["snowflake", "databricks", "bigquery", "all"], default="all")
    p.add_argument("--bq-key", help="path to BigQuery service-account JSON key")
    args = p.parse_args()

    want = ["snowflake", "databricks", "bigquery"] if args.engine == "all" else [args.engine]
    if "snowflake" in want:
        create_and_probe(args.org, build_snowflake(), SNOWFLAKE["probe_db"])
    if "databricks" in want:
        create_and_probe(args.org, build_databricks(), DATABRICKS["probe_db"])
    if "bigquery" in want:
        if not args.bq_key:
            print("\n=== BigQuery === SKIP: pass --bq-key <path to service-account JSON>")
        else:
            create_and_probe(args.org, build_bigquery(args.bq_key), "wax_baseball_dbt")


if __name__ == "__main__":
    main()
