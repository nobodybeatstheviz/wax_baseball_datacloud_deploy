# wax_baseball_datacloud_deploy — the repeatable D360 federation pattern

Zero-copy federation of the Keeping Score corpus into Salesforce Data 360,
built to run against ANY authed org. **Case #474498479 cleared 2026-09-03** — the
scratch org `keeping-score-w6a` is minted; the full **fully-headless** ordered
rebuild is **[`REPLAY-RUNBOOK.md`](REPLAY-RUNBOOK.md)** (read that to replay; this
README is the why). Everything here is generator-shaped:

0. `apply_connections.py --org <alias> --engine <snowflake|databricks|bigquery|all>` —
   creates the source connections **headlessly** via `POST /ssot/connections` (no GUI),
   reading creds from their standard local homes, then functionally probes each. The
   old "GUI floor" for connectors was disproven 2026-09-04 (see the headless note below).
1. `generate_payloads.py` — introspects the LIVE source schemas (Snowflake `snow` CLI,
   Databricks DESCRIBE, BigQuery API) and emits one Connect-API data-stream payload per
   stream into `payloads/`. Never hand-edit a payload; change the config list at the top
   and regenerate. **7 streams.**
2. `apply_datastreams.py --org <alias>` — POSTs each payload to
   `/services/data/v66.0/ssot/data-streams` using the CLI's auth for that
   alias (`sf org display`). Idempotent: streams that already exist are
   skipped. The org alias is the ONLY thing that changes for scratch-org replay.
3. `apply_dmo.py --org <alias>` — builds the `Attended_Games__dlm` DMO + its
   DLO→DMO mapping (the one object the SDM references as a Dmo, not a DLO).
4. `apply_sdm_shell.py --org <alias>` — creates the `Keeping_Score` model shell
   and adds its 7 data objects. **This closes the W4 gap** where the shell +
   data objects were built interactively through the d360 MCP and never scripted.
5. `apply_sdm.py --org <alias>` — relationships + calculated measures/dims.

`snowflake/grain_key_views.sql` is a Snowflake-side prereq (adds single-column grain keys
the marts lack). **Verified 7/7 on `keeping-score-w6a` 2026-09-04.**

## Headless connection creation (measured 2026-09-04 — corrects the earlier "GUI floor")

`POST /ssot/connections` creates a connection from the CLI's own Data 360 token — no browser.
The GUI is required ONLY for the `idp` auth path (a Salesforce-minted, read-only `externalId`
that appears only in the Setup dialog). The **non-IdP** paths — **Snowflake KeyPair**,
**Databricks PAT** — have no `externalId` and create fully headless. Both were created and
functionally probed with zero GUI.

## The federation split (ruled 2026-09-04: headless Snowflake + Databricks)

| Source | Connection | Streams | Auth |
|---|---|---|---|
| Snowflake `BASEBALL.WAX_BASEBALL` | `Snowflake_Baseball` | Attended_Games (→ `Attended_Games__dlm` DMO) · Fct_Game_Attendee · Fct_Plays · Fct_Attended_Team_Games · Fct_Hof_Sightings | KeyPair, headless ✅ |
| Databricks `lahman_baseball.baseball_data` | `Databricks_Baseball` | Lahman_People · Lahman_Hall_Of_Fame (SABR 2025) | PAT, headless ✅ |
| BigQuery | — | — | ⛔ connector is `ACCESS_CHECK` (org-entitlement wall) in this org — API open + creds valid, but "Failed to connect"; not client-fixable. Snowflake replaces it. `build_bigquery`/`bq_fields` stay ready for the day it's entitled. |

*History: devorg federated BigQuery+Databricks (Snowflake was region-blocked there —
`AWS_US_EAST_1` vs lakehouse `aws-prod2-apsouth1`). This fresh US org's lakehouse is
region-compatible with Snowflake, so the scratch build is Snowflake+Databricks.*

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

`apply_sdm_shell.py` creates the model shell + 7 data objects, then
`apply_sdm.py --org <alias>` replays relationships + calculated measures/dims.
*(Through 2026-09-03 the shell + data objects were built by hand via the d360 MCP;
that gap is now scripted — the d360 MCP is locked to devorg, so replay writes go
through `sf api request rest`.)*
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
