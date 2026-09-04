-- Grain-key views for the headless Snowflake federation (2026-09-04).
--
-- Data 360 DLOs require exactly ONE primary-key column. The Snowflake marts in
-- BASEBALL.WAX_BASEBALL are a stale load that predates the single-column grain
-- keys the BigQuery dbt marts carry (play_key, game_attendee_key, team_game_key),
-- so three of them have composite grain. These views add the same synthesized keys
-- the dbt models use (identical formulas), so the federated DLOs get a clean PK and
-- the SDM's apiNames/measures are unchanged. Attended_Games (wax_game_id) and
-- Hof_Sightings (player_id) already have single-column keys and need no view.
--
-- Apply headlessly:  snow sql -c wax_baseball_key -f snowflake/grain_key_views.sql

USE DATABASE BASEBALL;
USE SCHEMA WAX_BASEBALL;

-- Columns were loaded as QUOTED lowercase identifiers, so every reference (and the
-- synthesized key aliases) must be double-quoted or Snowflake folds them to uppercase.

CREATE OR REPLACE VIEW V_FCT_PLAYS AS
SELECT "game_id" || '-' || "event_id" AS "play_key", *
FROM FCT_PLAYS;

CREATE OR REPLACE VIEW V_FCT_GAME_ATTENDEE AS
SELECT "wax_game_id" || '-' || "attendee_key" AS "game_attendee_key", *
FROM FCT_GAME_ATTENDEE;

CREATE OR REPLACE VIEW V_FCT_ATTENDED_TEAM_GAMES AS
SELECT "game_id" || '-' || "team_id" AS "team_game_key", *
FROM FCT_ATTENDED_TEAM_GAMES;
