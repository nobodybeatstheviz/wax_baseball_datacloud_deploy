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

STREAMS = [
    # engine, connection,          database,               schema,            object,                    pk,                  stream name,               label,                      dlo name
    ("bigquery",   "BigQuery_Baseball",   BQ_PROJECT,        "wax_baseball_dbt", "fct_game_attendee",       "game_attendee_key", "Fct_Game_Attendee",       "Fct Game Attendee",        "Fct_Game_Attendee__dll"),
    ("bigquery",   "BigQuery_Baseball",   BQ_PROJECT,        "wax_baseball_dbt", "fct_plays",               "play_key",          "Fct_Plays",               "Fct Plays",                "Fct_Plays__dll"),
    ("bigquery",   "BigQuery_Baseball",   BQ_PROJECT,        "wax_baseball_dbt", "fct_attended_team_games", "team_game_key",     "Fct_Attended_Team_Games", "Fct Attended Team Games",  "Fct_Attended_Team_Games__dll"),
    ("bigquery",   "BigQuery_Baseball",   BQ_PROJECT,        "wax_baseball_dbt", "fct_hof_sightings",       "player_id",         "Fct_Hof_Sightings",       "Fct Hof Sightings",        "Fct_Hof_Sightings__dll"),
    ("databricks", "Databricks_Baseball", "lahman_baseball", "baseball_data",    "people",                  "playerID",          "Lahman_People",           "Lahman People",            "Lahman_People__dll"),
    ("databricks", "Databricks_Baseball", "lahman_baseball", "baseball_data",    "halloffame",              "playerID",          "Lahman_Hall_Of_Fame",     "Lahman Hall Of Fame",      "Lahman_Hall_Of_Fame__dll"),
]

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
    fields = bq_fields(schema, object_name) if engine == "bigquery" else dbx_fields(database, schema, object_name)
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
