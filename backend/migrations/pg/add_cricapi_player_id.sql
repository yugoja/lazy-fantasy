-- Add cricapi_player_id to players table for reliable player name matching (PostgreSQL).
-- Run: psql $DATABASE_URL -f migrations/pg/add_cricapi_player_id.sql

ALTER TABLE players ADD COLUMN IF NOT EXISTS cricapi_player_id VARCHAR(100);
CREATE UNIQUE INDEX IF NOT EXISTS uq_player_cricapi_id
  ON players(cricapi_player_id)
  WHERE cricapi_player_id IS NOT NULL;
