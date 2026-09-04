#!/usr/bin/env python3
"""Generate Data 360 data-stream payloads by introspecting the LIVE source schemas.

The generator is the artifact: payloads/ is disposable output. Add a stream by
adding one STREAMS entry and rerunning. Recipe + gotchas: see README.

Usage:  py generate_payloads.py
Needs:  google-cloud-bigquery (ADC), databricks-sql-connector (~/.databrickscfg
        profile wax_baseball) — both proven in the wax_baseball_parity repo.
"""

from __future__ import annotations

import configparser
import json
import pathlib

PAYLOAD_DIR = pathlib.Path(__file__).resolve().parent / "payloads"

BQ_PROJECT = "augmented-world-262319"
DBX_PROFILE = "wax_baseball"
DBX_HTTP_PATH = "/sql/1.0/warehouses/873a5fb5d84620c1"
SNOW_CONN = "wax_baseball_key"  # snow CLI connection (keypair)

# HEADLESS two-cloud federation (ruled 2026-09-04): Snowflake (WAX_BASEBALL marts) +
# Databricks (Lahman). BigQuery is dropped from this org — its connector is ACCESS_CHECK
# (org-entitlement wall, not client-fixable; the API is open and creds are valid, but the
# connector isn't provisioned for the scratch org). Snowflake replaces it, and both
# Snowflake + Databricks connections create fully headless (no GUI). The DLO names, SDM
# apiNames, relationships and measures are UNCHANGED — only the source underneath moved.
#
# Snowflake columns are quoted lowercase and match the measure field references. Three marts
# lack single-column grain keys (stale load) so we federate grain-key VIEWS instead
# (snowflake/grain_key_views.sql adds play_key/game_attendee_key/team_game_key).
STREAMS = [
    # engine, connection,          database,   schema,          object,                      pk,                  stream name,               label,                      dlo name
    ("snowflake",  "Snowflake_Baseball",  "BASEBALL", "WAX_BASEBALL", "FCT_ATTENDED_GAMES",        "wax_game_id",       "Attended_Games",          "Attended Games",           "Attended_Games__dll"),
    ("snowflake",  "Snowflake_Baseball",  "BASEBALL", "WAX_BASEBALL", "V_FCT_GAME_ATTENDEE",       "game_attendee_key", "Fct_Game_Attendee",       "Fct Game Attendee",        "Fct_Game_Attendee__dll"),
    ("snowflake",  "Snowflake_Baseball",  "BASEBALL", "WAX_BASEBALL", "V_FCT_PLAYS",               "play_key",          "Fct_Plays",               "Fct Plays",                "Fct_Plays__dll"),
    ("snowflake",  "Snowflake_Baseball",  "BASEBALL", "WAX_BASEBALL", "V_FCT_ATTENDED_TEAM_GAMES", "team_game_key",     "Fct_Attended_Team_Games", "Fct Attended Team Games",  "Fct_Attended_Team_Games__dll"),
    ("snowflake",  "Snowflake_Baseball",  "BASEBALL", "WAX_BASEBALL", "FCT_HOF_SIGHTINGS",         "player_id",         "Fct_Hof_Sightings",       "Fct Hof Sightings",        "Fct_Hof_Sightings__dll"),
    ("databricks", "Databricks_Baseball", "lahman_baseball", "baseball_data", "people",             "playerID",          "Lahman_People",           "Lahman People",            "Lahman_People__dll"),
    ("databricks", "Databricks_Baseball", "lahman_baseball", "baseball_data", "halloffame",         "playerID",          "Lahman_Hall_Of_Fame",     "Lahman Hall Of Fame",      "Lahman_Hall_Of_Fame__dll"),
]

SNOWFLAKE_TYPE_MAP = {
    "TEXT": "Text", "VARCHAR": "Text", "CHAR": "Text", "STRING": "Text",
    "NUMBER": "Number", "DECIMAL": "Number", "NUMERIC": "Number", "INT": "Number",
    "INTEGER": "Number", "BIGINT": "Number", "SMALLINT": "Number", "FLOAT": "Number",
    "DOUBLE": "Number", "REAL": "Number", "BOOLEAN": "Boolean", "DATE": "Date",
    "TIMESTAMP_NTZ": "DateTime", "TIMESTAMP_LTZ": "DateTime", "TIMESTAMP_TZ": "DateTime",
    "TIMESTAMP": "DateTime", "DATETIME": "DateTime", "TIME": "Text",
}

BQ_TYPE_MAP = {
    "STRING": "Text", "INTEGER": "Number", "INT64": "Number", "FLOAT": "Number",
    "FLOAT64": "Number", "NUMERIC": "Number", "BIGNUMERIC": "Number",
    "BOOLEAN": "Boolean", "BOOL": "Boolean", "DATE": "Date",
    "DATETIME": "DateTime", "TIMESTAMP": "DateTime", "TIME": "Text",
}

def dbx_type(t: str) -> str:
    t = t.lower()
    if t.startswith(("int", "bigint", "smallint", "tinyint", "double", "float", "decimal")):
        return "Number"
    if t == "boolean":
        return "Boolean"
    if t == "date":
        return "Date"
    if t.startswith("timestamp"):
        return "DateTime"
    return "Text"


def snow_type(t: str) -> str:
    return SNOWFLAKE_TYPE_MAP.get(t.upper().split("(")[0].strip(), "Text")


def snow_fields(database: str, schema: str, table: str) -> list[tuple[str, str]]:
    """Introspect a Snowflake table/view via the snow CLI (--format json).
    Column names are quoted lowercase; INFORMATION_SCHEMA returns them verbatim."""
    import json as _json
    import shutil as _shutil
    import subprocess as _subprocess
    snow = _shutil.which("snow") or sys.exit("snow CLI not found on PATH")
    q = (f"SELECT COLUMN_NAME, DATA_TYPE FROM {database}.INFORMATION_SCHEMA.COLUMNS "
         f"WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{table}' ORDER BY ORDINAL_POSITION")
    out = _subprocess.run([snow, "sql", "-c", SNOW_CONN, "-q", q, "--format", "json"],
                          capture_output=True, text=True)
    text = out.stdout.strip()
    start = text.find("[")
    if start == -1:
        raise SystemExit(f"snow introspection failed for {schema}.{table}: {(out.stdout or out.stderr)[:300]}")
    rows = _json.loads(text[start:])
    return [(r["COLUMN_NAME"], snow_type(r["DATA_TYPE"])) for r in rows]


def bq_fields(dataset: str, table: str) -> list[tuple[str, str]]:
    from google.cloud import bigquery
    client = bigquery.Client(project=BQ_PROJECT)
    schema = client.get_table(f"{BQ_PROJECT}.{dataset}.{table}").schema
    return [(f.name, BQ_TYPE_MAP.get(f.field_type.upper(), "Text")) for f in schema]


_dbx_conn = None

def dbx_fields(catalog: str, schema: str, table: str) -> list[tuple[str, str]]:
    global _dbx_conn
    if _dbx_conn is None:
        from databricks import sql as dbsql
        cfg = configparser.ConfigParser()
        cfg.read(pathlib.Path.home() / ".databrickscfg")
        _dbx_conn = dbsql.connect(
            server_hostname=cfg[DBX_PROFILE]["host"].replace("https://", ""),
            http_path=DBX_HTTP_PATH,
            access_token=cfg[DBX_PROFILE]["token"],
        )
    cursor = _dbx_conn.cursor()
    cursor.execute(f"DESCRIBE TABLE {catalog}.{schema}.{table}")
    fields = []
    for name, dtype, _comment in cursor.fetchall():
        if not name or name.startswith("#"):
            break  # partition/metadata section
        fields.append((name, dbx_type(dtype)))
    cursor.close()
    return fields


def build_payload(engine, connection, database, schema, object_name, pk, name, label, dlo_name) -> dict:
    if engine == "bigquery":
        fields = bq_fields(schema, object_name)
    elif engine == "snowflake":
        fields = snow_fields(database, schema, object_name)
    else:
        fields = dbx_fields(database, schema, object_name)
    if pk not in [f for f, _ in fields]:
        raise SystemExit(f"{object_name}: primary key column '{pk}' not found in source schema")
    return {
        # Gotchas honored: no 'datasource' key; DLO ends __dll; mappings present.
        "name": name,
        "label": label,
        "connectorInfo": {
            "connectorType": "DataConnector",
            "connectorDetails": {"name": connection},
        },
        "datastreamType": "EXTERNAL",
        "dataAccessMode": "Direct_Access",
        "advancedAttributes": {"database": database, "schema": schema, "object": object_name},
        "sourceFields": [{"name": f, "dataType": t} for f, t in fields],
        "mappings": [
            {"sourceFieldLabel": f, "targetFieldName": f, "targetFieldReturntype": t}
            for f, t in fields
        ],
        "dataLakeObjectInfo": {
            "name": dlo_name,
            "label": label,
            "category": "Other",
            "dataLakeFieldInputRepresentations": [
                {"name": f, "label": f, "dataType": t, "isPrimaryKey": f == pk}
                for f, t in fields
            ],
            "dataspaceInfo": [{"name": "default"}],
        },
        "refreshConfig": {
            "refreshMode": "TOTAL_REPLACE",
            "isAccelerationEnabled": False,
            "frequency": {"frequencyType": "None"},
        },
    }


def main() -> None:
    PAYLOAD_DIR.mkdir(exist_ok=True)
    for spec in STREAMS:
        payload = build_payload(*spec)
        out = PAYLOAD_DIR / f"{spec[6]}.json"
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        n = len(payload["sourceFields"])
        print(f"wrote {out.name}  ({n} fields, pk={spec[5]})")


if __name__ == "__main__":
    main()
