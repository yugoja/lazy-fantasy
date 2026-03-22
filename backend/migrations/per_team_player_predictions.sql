-- Migration: Split most_runs and most_wickets into per-team columns
-- Replaces 2 combined player columns with 4 per-team columns in both
-- matches and predictions tables.
--
-- Run once against the live DB:
--   sqlite3 lazyfantasy.db < per_team_player_predictions.sql

-- matches table
ALTER TABLE matches RENAME COLUMN result_most_runs_player_id TO result_most_runs_team1_player_id;
ALTER TABLE matches ADD COLUMN result_most_runs_team2_player_id INTEGER REFERENCES players(id);
ALTER TABLE matches RENAME COLUMN result_most_wickets_player_id TO result_most_wickets_team1_player_id;
ALTER TABLE matches ADD COLUMN result_most_wickets_team2_player_id INTEGER REFERENCES players(id);

-- predictions table
ALTER TABLE predictions RENAME COLUMN predicted_most_runs_player_id TO predicted_most_runs_team1_player_id;
ALTER TABLE predictions ADD COLUMN predicted_most_runs_team2_player_id INTEGER REFERENCES players(id);
ALTER TABLE predictions RENAME COLUMN predicted_most_wickets_player_id TO predicted_most_wickets_team1_player_id;
ALTER TABLE predictions ADD COLUMN predicted_most_wickets_team2_player_id INTEGER REFERENCES players(id);
