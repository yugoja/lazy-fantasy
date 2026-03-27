-- Add cricapi_player_id to players table for reliable player name matching.
-- Run: sqlite3 fantasy_cricket.db < migrations/add_cricapi_player_id.sql

ALTER TABLE players ADD COLUMN cricapi_player_id VARCHAR(100);
CREATE UNIQUE INDEX IF NOT EXISTS uq_player_cricapi_id
  ON players(cricapi_player_id)
  WHERE cricapi_player_id IS NOT NULL;
