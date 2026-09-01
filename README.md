# wax_baseball_datacloud_deploy — the repeatable D360 federation pattern

Two-cloud federation of the Keeping Score corpus into Salesforce Data 360,
built to run against ANY authed org (devorg today, the scratch org when
Partner case #474498479 clears). Everything here is generator-shaped:

1. `generate_payloads.py` — introspects the LIVE source schemas (BigQuery API,
   Databricks DESCRIBE) and emits one Connect-API data-stream payload per
   stream into `payloads/`. Never hand-edit a payload; change the config
   list at the top and regenerate.
2. `apply_datastreams.py --org <alias>` — POSTs each payload to
   `/services/data/v66.0/ssot/data-streams` using the CLI's auth for that
   alias (`sf org display`). Idempotent: streams that already exist are
   skipped. The org alias is the ONLY thing that changes for scratch-org replay.

## The federation split (ruled 2026-09-01: two clouds, third documented)

| Source | Connection | Streams | Mode |
|---|---|---|---|
| BigQuery `wax_baseball_dbt` | `BigQuery_Baseball` | fct_game_attendee · fct_plays · fct_attended_team_games (+ pre-existing Attended_Games, Dim_Attendee) | zero-copy `DIRECT_ACCESS` |
| Databricks `lahman_baseball.baseball_data` | `Databricks_Baseball` | people · halloffame (SABR 2025) | zero-copy `DIRECT_ACCESS` |
| Snowflake | — | — | ⛔ region mismatch, measured: Snowflake `AWS_US_EAST_1` vs this org's Data Cloud lakehouse `aws-prod2-apsouth1`. Zero-copy federation is region-coupled; align tenant regions at provisioning or plan an ingest path. The plays slice federates from BigQuery instead. |

## Load-bearing gotchas (from salesforce/reference/headless-bigquery-datastream-2026-08-22.md + this build)

- Use the GENERIC `data-streams` create with `connectorType: "DataConnector"` +
  the existing connection's name — the BigQuery-specific tool still says
  "not supported".
- `datasource` must be OMITTED for EXTERNAL streams (server sets it).
- DLO names MUST end `__dll`; exactly ONE field carries `isPrimaryKey: true`
  (the dbt marts carry explicit single-column grain keys for exactly this).
- `mappings` are REQUIRED at create even though list/get return `mappings: []`.
- Databricks discovery advancedAttributes are UPPERCASE (`DATABASE`, `SCHEMA` —
  DATABASE means Unity Catalog CATALOG); stream-create payloads use lowercase.
- A NEW org needs the two connections created first (GUI: BigQuery service
  account key + Databricks host/warehouse/PAT-as-password) — connector
  creation is the one non-headless step; everything after is this repo.

## The SDM (Keeping_Score) — verified 2026-09-01, all seven governed metrics exact

`apply_sdm.py --org <alias>` replays relationships + calculated measures/dims
(the SDM shell + data objects go through the d360 MCP, which works for those).
Golden battery through the semantic model: games 178 · stadiums 22 · HR 400 ·
runs 1706 · by-year exact (2001=17, 2003=17) · NYA 90/143 = .63 · top
attendees exact · Hall of Famers Seen 44.

SDM findings (each cost a real error):
- The d360 MCP's relationship create MANGLES the criteria array — relationships
  must go raw REST (`sf api request rest`). Its calc-measure update PATCHes
  where the API allows only PUT (delete + recreate instead).
- Creates WITHOUT an explicit apiName duplicate silently (auto-suffix `1`);
  with an explicit apiName they are idempotent. Always set apiName.
- A Text calc dimension rejects Integer expressions — the formula dialect is
  Tableau-flavored: STR(YEAR([...])).
- **Join-graph semantics**: a measure's query joins ONLY the objects its
  expression references. The HOF count over People+HallOfFame alone returned
  281 (all inducted players — nothing forced the "seen" path); adding
  [Plays] to the expression forced the four-way traversal and returned 35 —
  batters only, since the graph has a single People→Plays edge (batter_id).
  The contract's 44 (batters ∪ pitchers) rides the streamed fct_hof_sightings
  mart; the graph-native 35 is kept as HOF_Batters_Seen_Graph, the
  single-path-vs-union lesson made queryable. Query measures in MINIMAL
  graphs — unrelated-object fan-out is the failure mode.
