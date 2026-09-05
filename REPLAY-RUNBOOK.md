# Scratch-org replay runbook — the FULLY HEADLESS Keeping_Score D360 foundation

The ordered, source-controlled, **zero-GUI** rebuild of the entire Data 360 layer into a
fresh org. Target for the W6a sprint: **`keeping-score-w6a`** (PBO Dev Hub scratch org,
minted 2026-09-03, expires 2026-10-03).

**Headless proven end-to-end 2026-09-04.** The original "GUI floor" for connectors turned
out not to be a floor — `POST /ssot/connections` creates connections from the CLI's own
Data 360 token, no browser. Snowflake + Databricks federate fully headless; the whole
foundation is scripts. (BigQuery is dropped for this org — see the note at the bottom.)

## The two-cloud split (this org)

| Source | Connection | Streams | Auth (headless) |
|---|---|---|---|
| **Snowflake** `BASEBALL.WAX_BASEBALL` | `Snowflake_Baseball` | Attended_Games · Fct_Game_Attendee · Fct_Plays · Fct_Attended_Team_Games · Fct_Hof_Sightings | KeyPair (`~/.snowflake/wax_rsa_key.p8`) |
| **Databricks** `lahman_baseball.baseball_data` | `Databricks_Baseball` | Lahman_People · Lahman_Hall_Of_Fame | PAT (`~/.databrickscfg` profile `wax_baseball`) |

This replaces devorg's BigQuery+Databricks split (BigQuery → Snowflake), because Snowflake
holds every table and is the only GA/entitled zero-copy connector in the scratch org.

## The stack (bottom to top) — every layer headless

```
[ Snowflake prep ]  3 grain-key views (marts lack single-col PKs)       snowflake/grain_key_views.sql
      |
[ connections ]     Snowflake_Baseball + Databricks_Baseball            apply_connections.py   <- NO GUI
      |
[ streams ]         7 data streams -> 7 DLOs                            generate_payloads.py + apply_datastreams.py
      |
[ modeled ]         Attended_Games__dlm DMO + DLO->DMO mapping          apply_dmo.py
      |
[ semantic ]        Keeping_Score shell + 7 data objects                apply_sdm_shell.py
      |             relationships + calc measures + calc dims            apply_sdm.py
      |
[ verify ]          golden battery through /semantic-engine/gateway     parity_harness.py  (7/7)
```

6 of 7 data objects ride their DLOs directly; only `Attended_Games` is a DMO (its SDM
measures use title-cased fields — `[Attended_Games].[Wax_Game_ID]`, `[Venue]`, `[Game_Date]`).

## Prerequisites (headless, one-time per session)

- **Snowflake:** `snow` CLI connection `wax_baseball_key` (keypair; `~/.snowflake/wax_rsa_key.p8`).
- **Databricks:** `databricks` CLI profile `wax_baseball` (PAT); **the SQL warehouse must be RUNNING**
  when connections are created/tested and when the harness federates:
  `databricks --profile wax_baseball warehouses start 873a5fb5d84620c1`
  (serverless auto-stops on idle — restart it before a replay/verify run).

## The run, in order

```bash
cd C:/Users/georg/Documents/CODING/wax_baseball_datacloud_deploy
ORG=keeping-score-w6a

# 0. Snowflake grain-key views (idempotent; CREATE OR REPLACE)
snow sql -c wax_baseball_key -f snowflake/grain_key_views.sql

# 1. connections — HEADLESS, no GUI (creates + functionally probes each)
py apply_connections.py --org $ORG --engine snowflake
py apply_connections.py --org $ORG --engine databricks   # warehouse must be RUNNING

# 2. generate the 7 stream payloads (Snowflake introspection + Databricks DESCRIBE)
py generate_payloads.py

# 3. streams -> DLOs
py apply_datastreams.py --org $ORG

# 4. Attended_Games DMO + DLO->DMO mapping (reads live DLO field casing first)
py apply_dmo.py --org $ORG

# 5. SDM shell + 7 data objects (labels drive the apiNames step 6 references)
py apply_sdm_shell.py --org $ORG

# 6. relationships + calc measures + calc dims
py apply_sdm.py --org $ORG
```

## Verify (the acceptance gate — 7/7)

```bash
cd C:/Users/georg/Documents/CODING/wax_baseball_parity
databricks --profile wax_baseball warehouses start 873a5fb5d84620c1   # ensure RUNNING
D360_ORG=keeping-score-w6a py scripts/parity_harness.py
```

Golden battery, all exact: games 178 · stadiums 22 · HR 400 · runs 1706 · by-year (2001=17,
2003=17) · NYA 90/143 = .63 · Hall of Famers Seen 44. **Confirmed 7/7 on the scratch org
2026-09-04.**

## Gotchas that cost real time (all now handled in the scripts)

- **Connection creation is headless** via `POST /ssot/connections` — but only the non-IdP auth
  paths (Snowflake KeyPair, Databricks PAT). The `idp` path needs a GUI-minted `externalId`.
- **Snowflake private key** must be the base64 body only — strip the `-----BEGIN-----` PEM armor
  or you get `Illegal base64 character 2d`.
- **Databricks `jdbc_connection_url` is the BARE HOSTNAME** (`dbc-...cloud.databricks.com`), not a
  `jdbc:spark://` URL — and the warehouse must be RUNNING or you get `CONNECTION_NOT_ESTABLISHED`.
- **Snowflake columns are quoted lowercase** — refer to them with double quotes in the views, or
  Snowflake folds to uppercase (`invalid identifier 'GAME_ID'`).
- **DMO create must NOT send `objectType`** — the API rejects it (`Unrecognized field`).
- **Text calc dimension needs a String expression** — `STR(YEAR([...]))`, not `YEAR([...])`
  (`Invalid return type ... Actual: Integer, Expected: StringLiteral`).
- **The `sf.cmd` shim splits `&` in URLs** on Windows — keep query strings to a single param.
- **`sf api request rest --method DELETE` needs a `--body`** (even `{}`) or `No 'mode' found in 'body'`.
- Use `d360_connection_test` (`POST /ssot/connections/actions/test`) for a specific error — `create`
  collapses everything to a generic `INTERNAL_ERROR`.

## The GCP leg — GCS ingest (added 2026-09-05; BigQuery zero-copy stays walled, see below)

A third D360 model, `Keeping_Score_GCP`, over the same marts exported from BigQuery to Parquet in
Google Cloud Storage and **ingested** (copied) through the GA `GCS` connector — the entitled GCP
door. Ingest, not federation: the honest label. Everything headless.

```bash
# GCP side (once)
gcloud storage buckets create gs://wax-keeping-score-parquet --project=augmented-world-262319 --location=us-east1 --uniform-bucket-level-access
gcloud iam service-accounts create keeping-score-gcs --project=augmented-world-262319
SA=keeping-score-gcs@augmented-world-262319.iam.gserviceaccount.com
gcloud storage buckets add-iam-policy-binding gs://wax-keeping-score-parquet --member=serviceAccount:$SA --role=roles/storage.objectViewer
gcloud storage buckets add-iam-policy-binding gs://wax-keeping-score-parquet --member=serviceAccount:$SA --role=roles/storage.legacyBucketReader   # HeadBucket needs buckets.get
mkdir -p ~/.gcs && gcloud storage hmac create $SA --project=augmented-world-262319 --format=json > ~/.gcs/keeping-score-hmac.json   # secret to disk only

# data (rerun whenever the marts change)
cd C:/Users/georg/Documents/CODING/wax_baseball_parity && py scripts/export_bigquery.py     # 8 marts -> data/*.parquet
#   + lahman people / hall_of_fame from BigQuery `lahman` -> data/lahman_people.parquet, data/lahman_halloffame.parquet
for f in data/*.parquet; do n=$(basename $f .parquet); gcloud storage cp $f gs://wax-keeping-score-parquet/keeping-score/$n/$n.parquet; done

# D360 side
cd C:/Users/georg/Documents/CODING/wax_baseball_datacloud_deploy
py apply_connections.py --org $ORG --engine gcs          # GCS_Baseball; parentDirectory MUST end with '/'
py generate_payloads.py --engine gcs                     # pyarrow-introspected, S3-shape payloads -> payloads/gcs/
py apply_datastreams.py --org $ORG --dir gcs             # 7 *_GCP streams -> *_GCP__dll (created ACTIVE, empty)
py run_datastreams.py --org $ORG --suffix _GCP           # SERIAL runs (concurrent runs on one file connection fail)
py apply_sdm_gcp.py --org $ORG                           # shell + 7 objects, then relationships/measures/dims by introspection
```

Verify: `D360_ORG=$ORG py scripts/parity_harness.py` in `wax_baseball_parity` — the `d360_gcp` column.

Gotchas (all measured 2026-09-05, all handled in the scripts): `parentDirectory` without a trailing
slash → `CONNECTION_NOT_ESTABLISHED`; the connection **test** body is `connectorType, method,
credentials, parameters` (no `name`); the run endpoint is `/actions/run` (the MCP annotation says
`/run`); **runs must be serial**; semantic apiNames are suffixed **org-wide** (`Attended_Games2`,
`game_date8`) so the SDM generator reads the model back instead of predicting; the already-exists
error is spelled "Saving semantic entity failed: Unique…"; a successful DELETE is 204/empty; BigQuery
types Lahman `inducted` as BOOLEAN (`= true`, not `'Y'`); `TOTAL_REPLACE` dedupes on the DLO PK, so
`Lahman_Hall_Of_Fame_GCP` keeps one ballot row per `playerID` (1,543 of 6,426) until a composite key
is added.

## BigQuery — deferred (entitlement wall, not GUI, not client-fixable)

BigQuery's connector is `ACCESS_CHECK` release level in this scratch org. Measured 2026-09-04:
the `POST /ssot/connections` API accepts the request and the service-account key is provably
valid (direct `bigquery.Client` query returned 14,406 rows), but the D360 connector framework
returns `CONNECTORS_FRAMEWORK_TEST_FAILED: [BIGQUERY] [native] Failed to connect` — the
connector isn't provisioned/entitled for the org. No client action clears it (Snowflake +
Databricks are GA; BigQuery is not). `generate_payloads.py` keeps a `bigquery` branch and
`apply_connections.py` keeps `build_bigquery` ready for the day the entitlement lands, but a
Partner case on a scratch org is unlikely to move it — the working federation is Snowflake +
Databricks.
