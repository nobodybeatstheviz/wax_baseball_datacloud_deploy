# W6a — Tableau Next semantic model + Tableau Agent + YouTube action — BUILD LOG

The genuinely-new W6a work, opening on the verified headless D360 foundation
(`REPLAY-RUNBOOK.md`, 7/7 through the D360 semantic engine, org `keeping-score-w6a`
exp **2026-10-03**). Three pieces, in order:

1. **Tableau Next semantic model** over the `Keeping_Score` SDM
2. **Tableau Agent** — answers ≥2 golden questions matching reference values
3. **YouTube highlights action** — HTTP callout to YouTube Data API v3 (date + home + away)

This log is the working record for the sprint; findings graduate to the parity plan's
Post-round-2 rulings + the wax-baseball index on close.

---

## Measured foundation state (2026-09-04, session open)

Direct measurement against the scratch org before any build — not assumed.

- **Org:** `keeping-score-w6a` / `00DQL00000ahE0C2AU`, **Active**, API 67.0, exp **2026-10-03** (~29 days).
- **Features:** `CustomerDataPlatform`, `CustomerDataPlatformLite`, `TableauEinstein`. **No Agentforce feature.**
- **Metadata types (API 67.0):** no `Bot` / `GenAiPlanner` / `GenAiPlugin` / `TableauSemanticModel`
  types surface; the only AI type is `AiAgentScorerDefinition`. → **"Tableau Agent" here is the
  Tableau-Next-native agent (Tableau Einstein), NOT an Agentforce bot.** Piece-2 and the piece-3
  action mechanism reshape around that.
- **Tableau Next sObjects present:** `SemanticModelChangeEvent` (platform event),
  `TableauHostMapping` + `TableauHostMappingShare` (fields: `SiteLuid`, `UrlMatch`, `HostType`),
  `DataSemanticSearch` / `Feed` / `History`.
- 🔴 **`TableauHostMapping` = 0 rows** — no Tableau Next site is mapped/provisioned to this org yet.
  **This is step 0 of piece 1** and a candidate GUI/async-provisioning step. Resolve the provisioning
  path before authoring a semantic model.
- **CLI:** no `sf` Tableau plugin installed (only `custom-metadata 4.0.4`).

## Open parking-lot items (documented, revisit at their piece)

- 🅿️ **YouTube Data API v3 key does not exist.** Measured: `gcloud services api-keys list
  --project=augmented-world-262319` → **0 items**. The plan's "✅ minted 8/31" (line 191) is
  **stale**; P6 (line 67) still lists it open. Minting is cheap/headless and already ruled (8/31,
  no new account) — **re-mint when piece 3 opens**, restricted to YouTube Data API v3, then land as
  an org Named Credential.
- 🅿️ **`sf data query` breaks under Git-Bash on this machine** (`'C:\Program' is not recognized`) —
  other `sf` subcommands work. Workaround: `sf api request rest "/services/data/v67.0/query/?q=..."`
  (URL-encode, `+` for spaces). Use that for all SOQL reads this sprint.

## Research verdict (2026-09-04, grounded in Trailhead + dev docs)

**Piece 1 — semantic model: FULLY HEADLESS, and mostly already done.** There is no separate
"Tableau semantic model" object — **Tableau Next reuses the Data 360 SDM directly** as its
semantic layer ("Tableau Semantics is available in Data 360 and Tableau Next"; a TN workspace
"references existing semantic models from Data 360"). So **`Keeping_Score` (7/7 verified) IS the
TN semantic model.** Remaining piece-1 work = link a TN site to the org (the empty
`TableauHostMapping`) so a TN workspace can reference the SDM. SDM CRUD, if any is needed, is the
same `/ssot/…` Connect REST surface already in use (`d360_sdm_*`); no `sf project deploy` metadata
type for the SDM — the REST calls are the generator. AI-assist authoring ("Suggest
Relationships", "Draft with Einstein") is GUI-toggle-gated but not needed for headless authoring.

**Piece 2 — Tableau Agent: has a one-time GUI floor (the externalId-handshake analogue).**
"Tableau Agent" = the Agentforce **"Analytics and Visualization"** agent template; its
**Concierge: Analytics Q&A** subagent answers NL questions over the SDM. GUI-only steps:
(1) Setup → *Tableau Next Features* → enable **Agentforce for Analytics** (+ Concierge/Data
Pro/Inspector) — may auto-enable in recent scratch orgs; (2) Setup → *Agentforce Agents* → New →
Create from Template → **"Analytics and Visualization"**; (3) the **"Analytics Agent Readiness"**
pane on the SDM (agent guidelines). **After** that bootstrap the agent is standard Agentforce
metadata — **Bot / BotVersion → GenAiPlannerBundle (v64+) → GenAiPlugin (topics) → GenAiFunction
(actions)** — retrievable/deployable via `sf project retrieve/deploy`. ⚠️ **Squares with the
measured org state:** no `Bot`/`GenAi*` metadata types surface *yet* because the feature isn't
enabled — enabling it (step 1) should surface them. Minimum to answer questions: feature on →
agent from template → activate → permission set (Agent Access) assigned → SDM shared + agent-ready.
**Play: click steps 1–3 once, then `sf project retrieve` the agent metadata → version-controlled.**

**Piece 3 — HTTP action: FULLY HEADLESS + metadata-deployable.** Standard Agentforce action, not
TN-native. Two options: **(A) External Service** — register YouTube Data API v3 from an OpenAPI 3.0
schema pointed at a Named Credential; the operation becomes an invocable agent action directly (no
Flow/Apex). **(B) Flow HTTP Callout** — more param-mapping control. Either becomes a **GenAiFunction**
attached to a **GenAiPlugin** topic; the LLM planner extracts `date`/`homeTeam`/`awayTeam` from the
question and binds them. **Key storage: Named Credential + External Credential** (key never in
source). All types (`ExternalServiceRegistration`, Named/External Credential, Flow, GenAiPlugin,
GenAiFunction) deploy via `sf project deploy start`. Caveat: first External-Credential principal
activation can be finicky headlessly — build once in UI if the deploy balks, then retrieve.

**Revised sequence:** piece 1 (link TN site → SDM, headless) → piece 2 (one-time GUI bootstrap,
then retrieve metadata) → piece 3 (re-mint YouTube key → Named/External Credential + External
Service → GenAiFunction on the agent). **The single unavoidable GUI floor is piece-2 bootstrap** —
a genuine platform floor, same category as the D360 IdP externalId handshake.

- 🅿️ **Headless360 (H360) hosted MCP → the BigQuery `ACCESS_CHECK` question.** Wax's pin 9/4:
  H360 "might and should give the GCP federation answer quickly." Ask it first before any Partner
  case.
- 🅿️ **Salesforce GitHub repos — skills that complement the hosted MCPs.** Wax's pin 9/4: check
  `github.com/salesforce*` / `forcedotcom` for Claude skills/plugins that pair with the hosted
  servers (sobject-reads, metadata-experts, api-context, H360, Tableau Next).
- 🅿️ **Tableau Next Features left OFF (deliberate/gated):** *Data Analysis* subagent (needs
  **Waii** enabled in Data Cloud Setup → Feature Manager by a Data Cloud Architect) · *Data
  Connection and Analytics Creation (Beta)* agent template. Everything else on the page was
  enabled 9/4 (Tableau Agent · Beta Connectors · Semantic Model Curation · SDM AI Optimization ·
  Semantic Built-In AI · AI Semantic Description Generator · Following · Metric Insight Summary ·
  Template Builder · Templated D360 Home-Org Ops · Marketplace · Enhanced Viz Authoring · Q&A
  Calibration + feedback stream · Maps · Org Hierarchies · TN Auditing · Predictive Insights).

## GCP → D360 (Wax 9/5: "trying to federate gcp data into d360. we can do it!")

Measured 2026-09-05 on `keeping-score-w6a`, after the Beta Connectors toggle:

- **BigQuery connector still `ACCESS_CHECK`** (`GET /ssot/connectors` → 222 connectors: 95 GA ·
  119 BETA · **8 ACCESS_CHECK** incl. `BIGQUERY` and `REDSHIFT`). The toggle changed nothing.
  Auth options on it: `KeyPair` (SA private key) and `idp` (externalId `^app:DE809C7E:[0-9A-F]{8}$`).
- **The gate has a name.** `GoogleSpanner` (BETA) shows the mechanism explicitly: its BYOL feature
  carries `"accessCheck": "Gater.com.salesforce.cdp.unifiedIngestZeroCopy"` — ACCESS_CHECK is a
  **gater permission** Salesforce flips org-side. BigQuery's is almost certainly a sibling gater.
  🅿️ Ask **Headless360 MCP** (Wax's pin) which gater BigQuery needs and whether a Partner case
  can enable it on a scratch/PBO org.
- **The entitled GCP door: `GCS` (Google Cloud Storage) — GA**, `FileBased` ingest with
  `supportParquetFileType`, `supportDataSync`, `supportEnhancedRefresh`, `frequentIngest`, plus
  Egress. Attrs: `bucketName`, `parentDirectory`, `accessKey`, `secretKey` (GCS **HMAC** keys,
  S3-interop) — **no IdP externalId → headless-creatable** with `apply_connections.py`'s pattern.
  It's *ingest* (copy into DLOs), not zero-copy — the same local-hop-Parquet shape Path X used for
  Databricks, now with GCS as the hop.
- **Headless360 MCP asked (2026-09-05, Wax's pin) — 4 tools: `discover` · `describe` ·
  `dispatch_readonly` · `dispatch` (a recipe library + a `/ssot/mcp/execute` facade).** Verdict:
  BIGQUERY `ACCESS_CHECK` confirmed from the facade's own `d360_connector_list` (8 at that level:
  AdobeAnalytics2MI · BIGQUERY · DATACLOUD · DataCustomCode · FacebookPostInsightMI · InstagramMI ·
  REDSHIFT · ZoomInfo); **no gater/permission name exposed anywhere**; the reads that could name
  one — `GET /connect/gates`, `GET /setup/org/access/{name}`, `GET /setup/org/permissions/{name}` —
  **all 404 on this org**; Release Manager feature overrides `[]`; the data-streams recipe has a
  zero-copy create step for Snowflake only. Nuance: the facade's connector payload shows
  `accessCheck: "ACCESS_CHECK"` as a constant even on GA connectors, while the direct
  `/ssot/connectors/GoogleSpanner` read (my probe) showed the literal
  `Gater.com.salesforce.cdp.unifiedIngestZeroCopy` — two surfaces, two renderings of the same
  gate. **Conclusion: not flippable from any API on a PBO scratch org; a case is the only route,
  and GCS ingest (GA) is the entitled GCP door.** GCS existing connections: 0.
- 2026-09-05 — 🟢 **GCP → D360 LEG BUILT, HEADLESS, through the connection + 7 ingest streams.**
  GCP side: bucket `gs://wax-keeping-score-parquet` (us-east1, uniform access) · SA
  `keeping-score-gcs@augmented-world-262319` with `roles/storage.objectViewer` +
  `roles/storage.legacyBucketReader` on the bucket · HMAC key written by `gcloud storage hmac
  create --format=json` straight to `~/.gcs/keeping-score-hmac.json` (never printed) · marts
  exported by `wax_baseball_parity/scripts/export_bigquery.py` (8 marts, 15,591 rows) + Lahman
  `people` (24,270) and `hall_of_fame` (6,426) from BigQuery `lahman` → uploaded one folder per
  mart under `keeping-score/<mart>/<mart>.parquet`. **Two measured gotchas:** (1) the S3-interop
  `HeadBucket` needs `storage.buckets.get` — `objectViewer` alone → `CONNECTION_NOT_ESTABLISHED`;
  (2) **`parentDirectory` must end with `/`** (`keeping-score/` → `success:true`; `keeping-score`,
  `/`, `` → `CONNECTION_NOT_ESTABLISHED`). boto3 against `storage.googleapis.com` verified the
  HMAC key independently before blaming D360. D360 side: `apply_connections.py --engine gcs`
  (new `build_gcs`; the test endpoint wants `connectorType, method, credentials, parameters` —
  no `name`) → connection `GCS_Baseball` `9cgQL0000004HqHYAU`; `generate_payloads.py --engine
  gcs` introspects the **Parquet schemas with pyarrow** and emits the S3-shape stream body from
  the d360 MCP's own example (`datasource: "GCS"` · `datastreamType: CONNECTORSFRAMEWORK` ·
  `dataAccessMode: INGEST` · `advancedAttributes {fileName, importDirectory, fileType: PARQUET,
  headerlessRetrievalEnabled}`); `apply_datastreams.py --dir gcs` → **7/7 streams created**
  (`*_GCP`, DLOs `*_GCP__dll`), all ACTIVE with `lastRunStatus` null until run —
  `run_datastreams.py` (new) triggers `POST /data-streams/{id}/run` and polls.
- 2026-09-05 — 🟢 **`Keeping_Score_GCP` SDM BUILT BY INTROSPECTION (`apply_sdm_gcp.py`).**
  Shell + 7 DLO data objects (same labels as the original → same label-derived names) → read
  the model back → resolve every relationship criterion and every `[Object].[field]` token →
  5 relationships · 10 calc measures · 1 calc dim, all `_GCP`-suffixed. Gateway check:
  `Games_Attended_GCP` / `Unique_Stadiums_GCP` answer on the ingested Attended_Games DLO.
  **Four measured platform facts:** (1) **semantic apiNames are suffixed ORG-WIDE, not per
  model** — the GCP model's objects came back `Attended_Games1`… (then `…2` after the duplicate
  post below) because `Keeping_Score` owns the bare names; fields likewise (`game_date8`,
  `wax_game_id6`); resolve by label / suffix-strip, never predict. (2) The read-back field
  carries `dataObjectFieldName` (`wax_game_id__c`) + `label` + suffixed `apiName`. (3) The
  already-exists error for a model shell is spelled *"Saving semantic entity failed:
  Unique…"* — and it sits past the 300-char truncation, so the first run re-posted all 7 data
  objects (duplicates pruned with a `--prune-unreferenced` DELETE pass; **a successful DELETE
  is 204/empty body**, which the `sf` shim surfaces as `NON_JSON ""`). Data objects are now
  idempotent by label. (4) **BigQuery types Lahman `inducted` as BOOLEAN** (Snowflake/
  Databricks keep `'Y'/'N'` text) → `HOF_Batters_Seen_Graph` needs `= true` on this leg
  (`EXPR_FIXUPS`) — "Can't compare boolean and stringliteral" otherwise.
- 2026-09-05 — **Ingest runs: `POST /ssot/data-streams/{id}/actions/run`** (the MCP source's
  `@ApiEndpoint` says `/run`; the code builds `/actions/run`; only the latter exists).
  First pass ran all 7 concurrently: `Attended_Games_GCP` **SUCCESS (178 rows in
  `Attended_Games_GCP__dll`)**, the other six `FAILURE` within 30 s; a solo re-run of
  `Fct_Plays_GCP` then *ran for >10 min without failing* — concurrency on one file connection is
  the working hypothesis; remaining streams re-run one at a time. No run-history endpoint
  (`/runs`, `/run-history`, `/actions/runs` all 404); failures land in
  `problemRecordDataLakeObjectName` (`PR_<dlo>`), queryable via `/ssot/query-sql`.
- 2026-09-05 — **Concurrency confirmed:** re-run one at a time, `Fct_Hof_Sightings_GCP` ·
  `Fct_Game_Attendee_GCP` · `Fct_Attended_Team_Games_GCP` · `Lahman_Hall_Of_Fame_GCP` ·
  `Lahman_People_GCP` all **SUCCESS**; DLO counts 44 · 320 · 356 · 1,543 · 24,270. The
  problem-record DLOs were empty — the first-pass failures were job-level, not row-level.
  `run_datastreams.py` should run streams **serially by default** (todo: make `--suffix` iterate
  one at a time). Two open items: (a) **`Fct_Plays_GCP` stuck `PENDING`** (>40 min, 0 rows) after
  its first-pass collision — re-triggered, watching; (b) 🅿️ **`Lahman_Hall_Of_Fame_GCP` = 1,543
  rows of 6,426** — `TOTAL_REPLACE` on PK `playerID` keeps one ballot row per player (Snowflake/
  Databricks legs carry the full table; the SDM's `HOF_Batters_Seen_Graph_GCP` may undercount if
  the surviving row isn't the inducted one). Fix = a composite ballot key
  (`playerID_yearid_votedBy`) added in the export and used as the DLO PK — a generator change +
  stream recreate; parked until the parity run shows whether it bites.
- 2026-09-05 01:49 — **`Fct_Plays_GCP` SUCCESS, 14,406 rows** after a re-trigger (~55 min from
  first collision to landing; the second `/actions/run` on a PENDING stream returned
  `success:true` and did not error). **All 7 GCP DLOs populated:** 178 · 320 · 14,406 · 356 · 44 ·
  24,270 · 1,543 (HOF dedupe, see above).
- 2026-09-05 — 🟢 **PARITY 42/42 — six surfaces.** `parity_harness.py` with `d360_gcp`:
  G1–G5, G0a, G0b × bigquery · databricks · snowflake · d360 · tableau_next · **d360_gcp** all
  PASS; `parity-receipts.md` regenerated. Three clouds inside one D360 org (Snowflake zero-copy ·
  Databricks zero-copy · GCS ingest) answering one metric contract.
- **Proposed shape (RULED GO by Wax 2026-09-05 — "we can do this. lets go"):** BigQuery marts (`wax_baseball_dbt`) →
  `bq extract --destination_format PARQUET` → `gs://<new bucket>/keeping-score/<mart>/` → D360 `GCS`
  connection → 7 data streams → DLOs (parallel to the Snowflake ones) → the SDM's data objects
  re-pointed or a second SDM `Keeping_Score_GCP` for a three-cloud parity column. Existing bucket:
  `wax-ss49-spec-sheets` (US-EAST1) — SS49's, don't reuse; mint `wax-keeping-score-parquet`.

## Progress

- 2026-09-04 — session open; foundation measured (above). Research converged (verdict above).
  Reframe: piece 1 mostly done (SDM = TN semantic model); real work is the TN-site link + pieces
  2–3.
- 2026-09-04 — **`TableauHostMapping` red-herring correction (research round 2):** it's the
  *classic* Tableau-embedding host map (Tableau View/Pulse LWC), NOT the native TN tenant. Native
  TN has no separate site — the **live `Keeping_Score` SDM proves TN + Data 360 are provisioned.**
  So **piece 1 has no site gap.** The GUI enablement floor ("Turn on Tableau Next" + Data Cloud
  "Get Started") was already passed on this org. Remaining piece-1 = create a TN **workspace**
  referencing the SDM via the **Tableau Next REST API** (`/services/data/vXX.0/…`, JWT/ECA auth).
- 2026-09-04 — **Prereqs measured PRESENT + ASSIGNED:** license `Tableau Next Creator`
  (`TableauEinsteinUserPsl`, Active); my user (`005QL00000r1CzwYAE`) already holds permsets
  **`TableauEinsteinAdmin` + `TableauEinsteinAnalyst`** (the TN-REST-API prereq) + `CDPAdmin`.
  `Use Setup with Agentforce` permset exists → **Agentforce IS in the org**; the `Bot`/`GenAi*`
  metadata types are gated behind feature-enablement, not absent.
- 2026-09-04 — **Acceptance reframe:** since SDM = semantic model (done), a TN *workspace* is
  likely **optional** for W6a acceptance. The acceptance-critical path is **piece 2 (Tableau Agent
  answers ≥2 golden Qs) → piece 3 (YouTube action)**.
- 2026-09-04 — 🟢 **`sf agent` DX command family exists** (`agent create` from a spec YAML,
  `agent generate agent-spec`, `agent activate`, `agent preview`, `agent test`, `agent publish`,
  `agent adl` data libraries). So **agent create/activate/test is scriptable** — the research's
  "agent creation is a GUI wizard" is likely the connector-floor pattern again. Open: (a) whether
  the **Concierge / Analytics-and-Visualization** agent specifically is `sf agent create`-able or
  only auto-created on enablement; (b) whether **Agentforce-for-Analytics enablement** has a
  Settings-metadata path or is a genuine GUI-only toggle. **Attempting headless before declaring a
  floor** (per the 9/4 connector precedent). Next: probe `*Settings` metadata for the enablement.
- 2026-09-04 — **Wax ruled: try #2 headless, find the real floor; SCOPE EXPANDED — the Tableau
  Next MCP (partner org) is in scope** as a surface over the semantic layer (research in flight).
- 2026-09-04 — 🟢 **AGENTFORCE ENABLED HEADLESSLY — the assumed GUI floor dissolved (connector
  pattern repeats).** New DX project `CODING\wax_baseball_tableau_next` (API 67.0). Retrieved the
  candidate `Settings` (EinsteinGpt · EinsteinCopilot · Bot · Analytics · EinsteinAI ·
  AgentforceForDevelopers · CustomerDataPlatform · Ai4m). State found: `enableEinsteinGptPlatform`
  already true; **`enableEinsteinGptCopilot=false`** (the Agentforce master switch) and
  `enableBots=false`. Deployed `Settings:EinsteinCopilot` → **Succeeded**; that alone surfaced
  metadata types **`Bot` · `BotBlock` · `BotTemplate` · `GenAiPlannerBundle` · `GenAiPlugin` ·
  `GenAiFunction` · `AiEvaluationDefinition`** (274 → 277 types) and `BotDefinition` now queries
  (0 agents). **`Settings:Bot` (`enableBots`) FAILS headless:** *"Legal Terms acceptance and/or
  necessary feature dependencies required to enable Bot Settings"* — the Einstein Bots
  terms-acceptance click is a candidate genuine floor, **but likely not needed** for Agentforce
  agents (they surfaced without it). Local `Bot.settings-meta.xml` reverted to `false` to match the
  org. Deploys are all-or-nothing — a mixed batch rolls back the good component; deploy singly.
  Red herring: `EinsteinAgentSettings` is Service Cloud case-summarization, not Agentforce.
  `AnalyticsSettings` has no "Agentforce for Analytics" flag (candidates noted:
  `canExploreDataConversationally`, `enableReportingOnSDMPref`, both false — CRMA-side, untested).
- 2026-09-04 — 🟢 **Semantic-layer REST path FOUND by probe:** `GET /services/data/v67.0/ssot/semantic/models`
  → `{"count":1, items:[{"apiName":"Keeping_Score",…}]}` (the `/ssot/semantic-models` guesses
  404). `/services/data/v67.0/wave` answers (Tableau Next rides the Wave/CRMA REST root;
  `/wave/folders` → 403 FUNCTIONALITY_NOT_ENABLED). `/tableau`, `/connect/tableau`,
  `/tableau-next/*`, `/analytics/workspaces` all 404. Direct HTTP client works with
  `SF_TEMP_SHOW_SECRETS=true sf org display --json` (the plain `sf api request rest` shim 404s
  everything but `/query`).
- 2026-09-04 — **Tableau Next MCP — research verdict (grounded; full report in session):**
  it's the **Salesforce Hosted MCP server `analytics/tableau-next`** (GA Apr 2026; remote
  streamable-HTTP, no npm/local install): prod `https://api.salesforce.com/platform/mcp/v1/analytics/tableau-next`,
  sandbox/**scratch** `…/mcp/v1/sandbox/analytics/tableau-next`. **19 tools, all read-only**: SDM
  discovery (`list_semantic_models` · `get_semantic_model` · data objects · relationships ·
  measures · dimensions · metrics · calc dims/measures · logical view), workspaces/dashboards/viz
  list/get, and **`analyze_data`** = NL question routed through **Concierge** (needs Agentforce for
  Analytics + Concierge enabled). **No structured-query tool** on this server; writes only on the
  separate "Tableau Next Beta" server. **Auth = External Client App (not Connected App), scopes
  `mcp_api` + `refresh_token`, auth-code + PKCE, JWT tokens — browser login once per user, then
  refresh tokens live indefinitely** ("prevents automated or headless authentication" is Salesforce's
  stated design). Org-side steps per docs, all GUI: (1) ECA in Setup — **scratch orgs can't create
  ECAs in Setup UI**; metadata deploy (`ExternalClientApplication` + `ExtlClntAppOauthSettings`
  [+ `ExtlClntAppGlobalOauthSettings`, which flxbl reports scratch orgs reject]) is the candidate
  headless route — **measure**; (2) Setup → API Catalog → MCP Servers → toggle "Tableau Next" (~2
  min; needs Tableau Next Admin); (3) Concierge. Claude Code client: `claude mcp add --transport
  http --scope user --client-id <ECA key> --callback-port 38000 tableau-next <sandbox url>` then
  `claude mcp login tableau-next`; ECA callback = `http://localhost:38000/callback`; scratch orgs
  authorize at `test.salesforce.com`. `mcp-remote` unsupported. **Also on the map:** hosted
  `data/data-cloud-queries` (2 tools, `post_dc_query_sql`) can run `semantic_query()` SQL over
  `Keeping_Score` **without Concierge**; and `forcedotcom/d360-mcp-server` (already live, devorg-
  locked, client-credentials headless) has `d360_sdm_query` — the only zero-browser path today.
  Naming drift: Help calls the Q&A tool `query_semantic_data`, the dev reference `analyze_data`
  (the cert corpus copied the Help name — `salesforce/certs/tableau-next-cert/07-integrate/enable-tableau-next-mcp-server.md`).
- 2026-09-04 — 🟢 **EXTERNAL CLIENT APP CREATED HEADLESSLY in the scratch org** — the docs'
  "can't create ECAs in scratch orgs" is a *Setup-UI* limit only; **metadata deploy works** (no
  `ExternalClientApps` scratch-def feature needed on this org). `wax_baseball_tableau_next`:
  `externalClientApps/Wax_TN_MCP.eca` + `extlClntAppOauthSettings/Wax_TN_MCP.ecaOauth`
  (scopes **`MCP, RefreshToken`** — the enum is `MCP`, not `McpApi`; the error lists all valid
  scopes) + `extlClntAppGlobalOauthSets/Wax_TN_MCP.ecaGlblOauth` (callback
  `http://localhost:38000/callback`, PKCE required, secret optional, **`isNamedUserJwtEnabled`
  flipped true** — the hosted-MCP requirement; the org generates and returns the **consumer key**
  on retrieve, a public PKCE client id, kept in source). Global settings deploy only after OAuth
  settings succeed (order-dependent in one batch is fine). `ExtlClntAppOauthConfigurablePolicies`
  retrieve returned nothing (no policy record until first use).
- 2026-09-04 — **Two candidate GENUINE floors remain, both single Setup clicks (Wax's hands):**
  (1) **Setup → API Catalog → MCP Servers → toggle "Tableau Next"** (+ "Data Cloud queries") —
  GA servers are disabled by default; no REST surface found (`/mcp*`, `/connect/mcp*`,
  `/api-catalog*` all 404); `McpServerDefinition` metadata is for *custom* servers (docs 754:
  custom servers "be deployed via Metadata API") and its schema has no `label` — not the
  standard-server toggle. (2) **Setup → Tableau Next Features → Agentforce for Analytics →
  Concierge: Analytics Q&A** (+ the "Analytics and Visualization" agent template) — no metadata
  surface (`BotTemplate` empty; `AnalyticsSettings.canExploreDataConversationally` refuses;
  `Settings:Bot` refuses on legal terms). After (2), `sf project retrieve` the agent metadata.
  Then one **browser OAuth login** (`claude mcp login tableau-next`) — an auth ceremony, not a
  build step; refresh tokens persist after.
- 2026-09-04 — Hosted endpoint reachability: both scratch URL forms
  (`…/mcp/v1/sandbox/analytics/tableau-next` and `…/mcp/v1/d/drive-flow-1956-dev-ed/scratch/analytics/tableau-next`)
  answer **401** unauthenticated (expected; no `WWW-Authenticate` exposed).
- 2026-09-04 late — **Wax toggled the hosted servers in Setup → API Catalog → MCP Servers**
  (Tableau Next · **Tableau Next Beta** `analytics.tableau-next-pilot` · Data Cloud queries) and
  **Tableau Next Features → Tableau Agent** (+ most of the page; see parking lot). Then, headless:
  `claude mcp add --transport http --scope user --client-id <ECA key> --callback-port 38000` for
  `tableau-next` · `tableau-next-pilot` · `sobject-reads` (`platform/sobject-reads`) ·
  `data-cloud-queries` (`data/data-cloud-queries`), all on the `…/mcp/v1/sandbox/…` base;
  scratch-user password set via `sf org generate password`; Wax ran the four
  `claude mcp login <name>` browser logins → all four **✔ Connected** (refresh tokens persist).
  New servers aren't visible to an already-running session — drive them via
  `claude -p --allowedTools "mcp__<server>__*"` subprocesses (the pattern for this sprint).
- 2026-09-05 — 🟢 **TABLEAU NEXT MCP (GA) LIVE OVER `Keeping_Score`.** 19 tools confirmed by
  name. `list_semantic_models` → 1 (`Keeping_Score`, id `2SMQL0000002oFF4AY`, created by the 9/4
  headless replay). `get_semantic_model` returns the full model (78 KB): 7 data objects (Attended_Games
  DMO + 6 DLOs), **5 relationships intact**, 1 calc dimension (`Game_Year`), **10 calculated
  measures** (Games_Attended · Unique_Stadiums · Home_Runs_Witnessed · Runs_Witnessed ·
  Team_Wins_Attended · Team_Games_Decided · Attended_Win_Rate · Games_per_Attendee ·
  Hall_of_Famers_Seen · HOF_Batters_Seen_Graph). Two model facts that matter: **`semanticMetrics: []`**
  — in Tableau Next a *metric* is a separate governed object layered on a measure, so the "7
  governed metrics" exist here only as calculated measures until promoted (`add_semantic_model_metric`
  on the Beta server); and **`agentEnabled: false`** — the Analytics-Agent-Readiness flag, the
  likely gate on `analyze_data`. Also observed: the `HOF_Batters_Seen_Graph` expression comes back
  with HTML-escaped quotes (`&#39;Y&#39;`) — display artifact vs stored literal to be verified by
  query. Suffix rule: repeated field names across DLOs get numeric suffixes (`game_date1`,
  `wax_game_id2`, `playerID1`) and relationship criteria reference the suffixed apiNames.
- 2026-09-05 — 🟢 **TABLEAU NEXT BETA MCP = 155 TOOLS, the headless WRITE path.** Includes
  `create_workspace` · `create_semantic_model` · `add_semantic_model_{metric,measure,dimension,
  calculated_measure,calculated_dimension,relationship,data_object,logical_view,parameter}` ·
  `create_visualization` / `edit_visualization` · `create_dashboard` / `add_widget_to_dashboard` /
  `add_dashboard_page` / `add_global_filter_to_dashboard` · `create_alert` · `create_data_stream` ·
  `create_data_model_object` · `create_dlo_to_dmo_mapping` · `create_data_transform` ·
  `run_semantic_query` · `generate_questions` · `generate_description` · `generate_business_preference`
  · `analyze_data` · promotion/reuse requests · asset shares. **This retires the "TN REST workspace
  endpoint undiscovered" gap and reopens the viz lane (V1) headlessly, on the Beta terms.**
- 2026-09-05 — 🟢 **PIECE 2 ACCEPTANCE MET — Tableau Agent (Concierge) answers the golden
  battery, with NO agent wizard, NO `BotTemplate`, `agentEnabled:false` on the model.** The
  "Tableau Agent" feature toggle alone made `analyze_data` live. Impersonal phrasing:
  *"What is the total Games Attended across the whole model?"* → **178** · *"What is the total
  Home Runs Witnessed?"* → **400** · *"Show Games Attended by Game Year for 2001 and 2003"* →
  **17 / 17**, plus an unprompted full `vizMetadata` bar-chart spec (rows F1=Game_Year,
  columns F2=Games_Attended, filter In [2001,2003]). Each answer carries `troubleshootingInfo`
  with the literal structured semantic query it ran + a `traceId` — **this is the Tableau Agent
  cell of the O-matrix, measurable.** Phrasing miss, not engine: *"What is Unique Stadiums?"*
  returned the measure's definition (a "what is X" reads as a definition request).
- 2026-09-05 — 🔴 **FINDING — the "who is *I*" filter.** First-person phrasing (*"How many games
  have I attended?"*) made Concierge resolve *I* to the running user's Salesforce Id and silently
  inject `Game_Attendee.attendee_key EqualsIgnoreCase '005QL00000r1Czw'` → **0 home runs, 0
  stadiums, answered confidently** ("You didn't witness any home runs… a unique insight!"). Q1
  asked who *I* am instead of querying. The whole model is one person's attendance, so the
  row-level *I* filter is wrong by construction — the personal-data agent question (index § the
  agent-action question) made concrete, and a grounded-but-wrong-filter class for the O-matrix
  (visible only in the trace). Fix candidates, not yet tried: model **business preferences /
  agent guidelines** ("this model is Wax's attendance; *I* = the whole model") via
  `update_semantic_model_business_preferences` (currently none set — the field is absent from the
  response), or the Analytics-Agent-Readiness pane. Ruling wanted before writing to the model.
- 2026-09-05 — 🟢 **7/7 THROUGH THE TABLEAU NEXT BETA MCP `run_semantic_query`** (fifth parity
  surface): A `Games_Attended, Unique_Stadiums, Home_Runs_Witnessed, Runs_Witnessed` → **178 · 22 ·
  400 · 1706** · B `Hall_of_Famers_Seen` → **44** · C `HOF_Batters_Seen_Graph` → **35** (matches the
  W5 grain-level figure; the `&#39;` in the expression was a display artifact) · D by `team_id`
  (`table_field {name:'team_id', table_name:'Attended_Team_Games'}`, ROW_GROUPING) → **NYA 90 / 143
  / 0.63**. Query shape: `structuredSemanticQuery` is proto-shaped snake_case
  (`fields[].expression.semantic_field.name`, `grouping:"ROW_GROUPING"`); response is
  `defaultExc` (a JSON string) → `queryResults.queryData.rows[].values`. **Known limits:** (1)
  all six measures in one call → `USER_ILLEGAL_ARGUMENT_RELATIONSHIP_NO_PATH_ERROR` — the same
  D360 join-graph gap as W4/W5 (`HOF_Sightings` has no edge to `Attended_Games`); split by join
  tree. (2) Filter proto: `comparison_predicate` is not a field of `…querypreparer.v1.Predicate` —
  the filter oneof name is unknown (🅿️ look up via the schema before the harness capture).
  `get_semantic_model_business_preferences` returns the model with no `businessPreferences` key.
- 2026-09-05 — 🟢 **"Who is *I*" FIXED by model business preferences (Wax ruled "hell yeah").**
  `mcp__tableau-next-pilot__update_semantic_model_business_preferences` wrote the doctrine text
  (Source copy: `wax_baseball_tableau_next/semantics/keeping-score-business-preferences.md`) into
  `businessPreferences` on `Keeping_Score`; readback intact (apostrophes/quotes come back
  HTML-entity-encoded). Re-test, first person: *"How many home runs have I witnessed?"* → **400**;
  *"How many games have I attended in total?"* → **178** — both traces show the bare governed
  measure with **no attendee filter and no dimension filter**. **The lesson: Concierge's
  first-person resolution defaults to the running user's Id; a personal-data model must say so
  in its business preferences or *I* silently means "rows tagged with my user Id" → confident
  zeros.** Business preferences are per-model doctrine — the same shape as the agent
  guidelines the Readiness pane would hold — and they're writable headlessly.
- 2026-09-05 — **Ruling (Wax): piece-3 actions are Salesforce-world — Flow or Agentforce
  actions.** So the YouTube action attaches to an Agentforce agent (template "Analytics and
  Visualization", or the Baseball_Scout shape), not to Concierge. Carded for a peak block.
- 2026-09-05 — 🟢 **GENERATORS SHIPPED + RUN (Wax: "yes on 2 and 3").** `wax_baseball_tableau_next`
  committed (`2356ef9`: Settings + ECA metadata + business-preferences Source + README).
  `wax_baseball_parity` gained `scripts/_hosted_mcp.py` — a deterministic MCP-over-HTTP client that
  reuses Claude Code's OAuth for a hosted server (`~/.claude/.credentials.json` →
  `mcpOAuth/<server>|<hash>/accessToken`; initialize → initialized → tools/call; **never refreshes**,
  because the ECA rotates refresh tokens and a script refresh would invalidate Claude's copy — on 401
  it says to run any `claude -p` against the server). **Parity harness: `tableau_next` is the fifth
  column** — the d360 spec re-dialected to snake_case (`to_snake_query`) and sent to
  `tableau-next-pilot` `run_semantic_query`; **35/35 PASS** (G1–G5, G0a, G0b × bigquery ·
  databricks · snowflake · d360 · tableau_next), `parity-receipts.md` regenerated.
  **O-matrix: `observability/capture_tableau_agent.py`** captured G2 first-person → **400**
  (traceId `1dfa807e…`, turn 9,085 ms + 1,025 ms session, query = bare `Home_Runs_Witnessed`, no
  filter, no viz spec) + the games question → 178; `extract_observability.py` gained
  `parse_tableau_agent_trace` / `tableau_agent_cell` / a render section → `observability-receipts.md`
  **6/6 measured** (the surfaces.json "read" row for Tableau Agent is superseded automatically).
  Cell verdict: no reasoning text but the plan is legible as the chosen query; structured query
  verbatim, no SQL; grounding named (`sdmApiNames`); tokens absent, latency self-timed, `traceId`
  the only server handle; retrieval = MCP over HTTP with an ECA — the first Tableau surface here
  with an API-retrievable trace.
- 🅿️ **Harness/O-matrix generator work now unlocked:** *(DONE 2026-09-05 — see above; kept for
  the original framing)* a `capture_tableau_next.py` in
  `CODING\wax_baseball_parity` (Analysis layer) driving `claude -p --allowedTools
  "mcp__tableau-next*__*"` — the OAuth token lives in Claude Code's store, so the subprocess is
  the headless path — to (a) add the Tableau Next column to `parity-receipts.md` (7/7 above) and
  (b) measure the Tableau Agent cell of `observability-receipts.md` from `troubleshootingInfo`.
- 2026-09-04 — **TN REST endpoint path (workspaces) — SUPERSEDED by the Beta MCP above** — `/services/data/v67.0/connect`
  root = NOT_FOUND; dev-docs host 403s automated fetch. Needs org introspection or a browser grab
  of the [TN REST API Get-Started](https://developer.salesforce.com/docs/analytics/tableau-next-rest-api/guide/get-started.html) path. Deferred (workspace may be optional).
- 2026-09-06 — **PIECE 3 OPENED. YouTube key re-minted** on `augmented-world-262319`, restricted to
  YouTube Data API v3, keyString only in `~/.gcs/keeping-score-youtube-key.json`. ⚠️ Lesson: `gcloud
  services api-keys create` prints the operation result — keyString included — to **stderr**, so a
  stdout redirect leaks it (the HMAC command writes to stdout; same CLI, two streams). First mint
  leaked to console → deleted, re-minted with both streams suppressed. Verified live via the
  `X-Goog-Api-Key` **header** (the injection a Named Credential does cleanly; no `key=` query param).
- 2026-09-06 — 🟢 **CREDENTIAL CHAIN HEADLESS, FIRST TRY.** `wax_baseball_tableau_next`:
  `YouTube_API` External Credential (Custom protocol, `YouTube_Principal`) + `YouTube_Data_API`
  Named Credential (`https://www.googleapis.com`, custom header `X-Goog-Api-Key =
  {!$Credential.YouTube_API.ApiKey}` — HttpHeader params need `sequenceNumber`) +
  `YouTube_API_Access` permset (principal access; Employee Agent = assign to every chatting user,
  the W7 lesson). The principal secret landed via `POST /named-credentials/credential`
  (`scripts/set_youtube_credential.py` — direct HTTP; the `sf api request rest` shim 404s every
  Connect endpoint but `/query`). The runbook's "finicky principal activation" never bit. Anonymous
  Apex through `callout:YouTube_Data_API` → **HTTP 200**, real highlight results.
- 2026-09-06 — 🔴 **FINDING — External Service actions don't fit Agent Script.** ESR
  `YouTubeHighlights` deployed fine (ESR names are **alphanumeric-only**, no underscores) and
  generates invocable `YouTubeHighlights.searchHighlights` — but its response output is literally
  named **`200`**, and the Agent Script compiler rejects `200` as an identifier (quoted too). Flow
  hits the same wall differently: the `200` output is a generated Apex-defined type a hand-written
  Flow XML can't bind stably. Resolution: **thin invocable Apex wrapper** (`GameHighlightsSearch.cls`,
  W7's proven `apex://` shape) renaming outputs to `videos`/`videoCount`/`hasData`; the key still
  rides the External Credential principal — the ESR stays deployed as the registered API contract.
  Second publish-time rule: Apex `Integer` outputs must be declared `object` +
  `complex_data_type_name: "lightning__integerType"` (the publisher's own error says so exactly).
- 2026-09-06 — **`Highlight_Scout` authored as an Agent Script authoring bundle** (aiAuthoringBundles;
  `sf agent generate agent-spec` is walled — `AgentforceAiAssist` not enabled on this org type — but
  hand-authored Agent Script needs no LLM assist; `sf agent validate authoring-bundle` → OK).
  ⛔ **`sf agent publish authoring-bundle` blocked mid-session by a network outage**: the scratch-org
  authoring API lives on `test.api.salesforce.com`, whose ingress (`test1-uswest2.aws.sfdc.cl`, 3 AWS
  IPs) stopped answering TCP entirely — measured from two DNS resolvers; `api.salesforce.com` (prod,
  155.226.x — Salesforce-owned ingress) answers fine, and the lib only falls through to `test.` on
  404, so no client-side override helps. It answered a publish validation 400 minutes earlier —
  transient outage, watcher polling. Test spec ready: `tests/Highlight_Scout-youtube-action.yaml`
  (Yankees–Royals 2024-10-05 ALDS — an attended game).
- 2026-09-07 — **`test.api.salesforce.com` outage CONFIRMED Salesforce-side (not client).** Persisted
  >12 h across a session restart. Diagnosed to exhaustion: the scratch-org agent-authoring ingress
  resolves to 3 AWS us-west-2 IPs (`34.210.29.116` · `44.228.60.86` · `34.213.108.10`) that silently
  drop TCP:443 (12 s timeout, not a refusal) from **three independent network paths** — home
  broadband, in-laws' broadband, and 5G cellular. Client is clean: no proxy (`netsh winhttp` direct),
  no Windows Firewall block rule, no blackhole route (routing to the IPs is normal via the gateway),
  no third-party firewall product. Controls all pass from the same laptop: `api.salesforce.com`
  (Salesforce IP space `155.226.144.x`) 200/404, the scratch org host 200, and `s3.us-west-2`
  (a *different* AWS us-west-2 IP) connects — so it's neither a broad AWS nor an ISP outage, only
  those 3 ingress IPs. The publisher tries prod first then falls to `test.` on 404, and a scratch
  org's authoring API 404s on prod → it must use `test.api`, so there's no client-side override.
  **Piece 3 is build-complete and staged — bundle validated, credential chain proven with a live
  callout 200, test spec written — pending ONLY Salesforce restoring that ingress.** Retry
  `sf agent publish authoring-bundle --api-name Highlight_Scout -o keeping-score-w6a` on a normal
  service day; then activate + run the end-to-end demo.
- 2026-09-09 — ⛔ **The 9/6–9/7 "outage" diagnosis was WRONG — it's a CLI bug, and the host never
  worked.** `forcedotcom/cli#3634` (filed 2026-08-28, before our first attempt; labels bug ·
  validated · investigating; Salesforce work item W-24023175) describes this exact failure. Read
  from the library on this machine (`@salesforce/agents` 2.0.4 `lib/utils.js`
  `requestWithEndpointFallback`): publish POSTs `/einstein/ai-agent/v1.1/authoring/agents` to prod
  `api.salesforce.com` → 404 empty body for scratch orgs / Agentforce DEs → falls back to
  `test.api.salesforce.com`, whose CNAME is `ingress-internal.core4.test1-uswest2.aws.sfdc.cl` —
  **internal-only by name**, never accepts public TCP — and the loop throws on the timeout before
  trying `dev.api` (CNAME `ingress-internal.core002.dev1-uswest2...`, equally dead). Re-measured 9/9:
  `test.` and `dev.` time out from here AND from an external fetcher; prod 404 in 0.1 s; scratch host
  200; Trust API 0 active incidents. The 9/6 "validation 400 minutes earlier" was the `/scripts`
  route on prod (what `sf agent validate` uses) — a different route on a different host. Lesson: the
  one check that would have caught it was reading the CNAME target, which literally says "internal";
  a days-long silent failure with no Trust posting is "by design," not "down." **Ruled (Wax):**
  reproduction posted to #3634 from this scratch org (CLI 2.149.9 · agent plugin 2.0.3 · node
  22.19.0 · API 67.0); publish `Highlight_Scout` through Agentforce Builder's Agent Script editor in
  the UI — one GUI step in the headless thread, recorded as a platform finding — then activate + run
  the end-to-end demo. Headless publish returns when #3634 ships.
- 2026-09-09 — ⛔ **The UI path hit the real wall: `keeping-score-w6a` has no Agentforce.** Setup →
  Agentforce Agents: toggle Off + "You don't have the required permissions" for the SysAdmin user;
  assigning `UseSetupWithAgentforce` changed nothing. Measured: the only PermissionSetLicense is
  `TableauEinsteinUserPsl`; `Settings:AgentPlatform` is an *unknown type* here; the scratch def had
  only `EnableSetPasswordInApi`. Salesforce's own samples (`trailheadapps/agent-script-recipes`,
  `coral-cloud`) mint with feature **`Einstein1AIPlatform`** + `agentPlatformSettings.enableAgentPlatform`.
  So the 9/4 "Agentforce enabled headlessly" was half right — `enableEinsteinGptCopilot=true`
  surfaced the `Bot`/`GenAi*` metadata types and let `validate` pass, but the *product* needs the
  feature, and features are fixed at mint. **Correction to the 9/4 lesson: metadata types surfacing
  ≠ the feature being licensed; check `PermissionSetLicense` before declaring a floor dissolved.**
- 2026-09-09 — 🟢 **PIECE 3 LIVE IN `devorg` — HEADLESS END TO END.** Ruled path A (re-mint
  rejected: hours, resets the clock, one demo). Stack committed to the tableau-next repo first
  (`70d1b71`; it had been untracked — the 9/4 evaporation lesson), then to devorg: deploy 6
  components ✓ · `set_youtube_credential.py devorg` ✓ · permset ✓ · callout 200 ✓ ·
  **`sf agent publish authoring-bundle` → published in 18 s, no GUI** — prod `api.salesforce.com`
  serves `/authoring/agents` for this Agentforce DE, so #3634's fallback never fires; follow-up
  posted to the issue (the chain turns "unlicensed org" into a fake network failure; suggested an
  entitlement check + a named-host error). `sf agent activate` → v1 active (devorg now holds
  Baseball_Agent · Baseball_Scout · Superstore_Signal · Highlight_Scout). **Testing Center ran
  end-to-end, 16 s, not wedged** (`Highlight_Scout_Test`, created from the spec): topic 3/3 ·
  action 3/3 · outcome 2/3. Case 2 (Red Sox–Rays 5/14/24) and case 3 (off-topic honesty) pass.
  **Case 1 miss is a real finding:** for the 10/5/24 ALDS game the search returned the whole series
  (Games 1, 3, 4 — 10/5, 10/9, 10/10) and the agent presented all three, exactly as its "use ONLY
  the output" instruction says — grounded, not invented, but unfiltered by date. Fix candidates:
  a date/title filter in `GameHighlightsSearch` (Apex side, deterministic) or a "prefer the
  date-matched video" line in the topic instructions (LLM side). Wax rules. Receipt on disk:
  `test-results/test-result-4KBdL0000002ELRWA2.txt` (URLs redacted by the runner).
  `sf agent preview send` takes `-u/--utterance` AND `-n <agent>` alongside `--session-id`.
- 2026-09-09 — 🔴 **FINDING: the same utterance, minutes apart, produced opposite behaviors.**
  Testing Center: `search_highlights` called, 3 videos returned. Live `sf agent preview`
  (`--use-live-actions`), same published v1: **no action call at all** — the trace
  (`.sfdx/agents/0XxdL000004GFK9SAO/sessions/01a088e4-…/traces/`) shows
  UserInput → topic_selector LLMStep → Transition → game_highlights → **one LLMStep →
  PlannerResponse**, zero `search_highlights` invocation, and the reply *"No highlights were found
  for the Yankees vs Royals game on October 5, 2024"* — a **fabricated no-result**, stated in
  defiance of the topic's own "you MUST call search_highlights" instruction. This is the O1
  failure class (the 9/3 no-action answer) reproduced on a one-action agent with the strongest
  instruction phrasing available: an instruction is not a gate. Design consequence for ADR §7:
  the Apex action should be the *only* path to a "found / not found" statement — e.g. require the
  action output variable to be populated before the topic may respond (Agent Script
  `if`-gating on `@variables`), or make the topic's response node unreachable without the action.
  Wax's call on which. Both runs are receipts: the Testing Center file + the preview trace dir.
- 2026-09-06 — 🔴 **HOF DEDUPE BITES: `HOF_Batters_Seen_Graph_GCP` = 24 vs 35.** The parked
  condition fired on direct measurement — the G-battery never exercises this measure (G5=44 rides
  `fct_hof_sightings`; the receipts' 42/42 was silent on the deduped Lahman table). Fix executed as
  ruled: `ballot_key = playerID_yearid_votedBy` (verified unique over all 6,426 rows in BigQuery)
  derived in `export_bigquery.py` — which now **generator-owns the Lahman exports** (they'd been
  ad hoc) — stream PK flipped in `generate_payloads.py`, parquet re-uploaded. Recreate sequence
  measured: the stream DELETE returns **412 CANNOT_DELETE_ENTITY while the SDM references the DLO**
  (the `sf` shim swallows the 412 as an empty 204-looking body — direct HTTP showed it); detach
  order that works: calc measure `HOF_Batters_Seen_Graph_GCP` → relationship
  `Player_to_Hall_of_Fame_GCP` → data object → stream+DLO (all 204), deletion propagates async
  (~seconds), then `apply_datastreams.py` recreates (pk=ballot_key) and `apply_sdm_gcp.py` re-adds
  the detached trio idempotently. Ingest re-run in flight; acceptance = graph measure back to 35 +
  full harness rerun.
- 2026-09-06 — 🟢 **HOF COMPOSITE KEY VERIFIED: `HOF_Batters_Seen_Graph_GCP` 24 → 35 = reference.**
  Recreated stream ran SUCCESS on the first serial trigger; `Lahman_Hall_Of_Fame_GCP__dll` = **6,426
  rows** (was 1,543). The SDM re-add came back as `Lahman_Hall_Of_Fame1` (org-wide suffix rotation,
  as designed) and the generator re-resolved relationship + measure against it untouched.
- 2026-09-06 — ⚠️ **Harness rerun: 5 surfaces × 7 = 35/35 PASS (incl. the fixed d360_gcp); the
  `tableau_next` column is auth-walled, not mismatched.** The `tableau-next-pilot` OAuth in Claude
  Code's store is gone/expired (~1 day after mint — the 9/5 "refresh tokens live indefinitely" read
  is falsified for this ECA config); a `claude -p` subprocess can't restore it — re-auth is the
  browser ceremony by design. `parity-receipts.md` currently reads "❌ MISMATCH" from the auth
  errors — regenerate after **Wax runs `claude mcp login tableau-next-pilot` (+ `tableau-next`)**;
  values are expected unchanged (the SDM under it is untouched, and d360 reads the same model 7/7). A curated skills
  library (100+) with Claude Code plugins under `plugins/builder/` — `salesforce-development`
  auto-detects a DX project and resolves **Skills → Salesforce CLI → hosted MCP** in that order;
  skills directly adjacent to this build: `agentforce-generate` · `agentforce-test` ·
  `agentforce-observe` · `agentforce-d360-analyze` · `agentforce-architecture-analyze` ·
  `data360-schema-get` · `data360-code-extension-generate` · `platform-observability`. Install is
  `npx skills add forcedotcom/sf-skills` (or the plugin). Jaganpro/sf-skills is archived into
  `forcedotcom/afv-library`. Not installed — Wax's call.
