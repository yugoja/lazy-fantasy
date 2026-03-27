-- Add sport column to tournaments, teams, and leagues tables (PostgreSQL).
-- Run: psql $DATABASE_URL -f migrations/pg/add_sport_column.sql

ALTER TABLE tournaments ADD COLUMN IF NOT EXISTS sport VARCHAR(20) DEFAULT 'cricket';
UPDATE tournaments SET sport = 'cricket' WHERE sport IS NULL;

ALTER TABLE teams ADD COLUMN IF NOT EXISTS sport VARCHAR(20) DEFAULT 'cricket';
UPDATE teams SET sport = 'cricket' WHERE sport IS NULL;

ALTER TABLE leagues ADD COLUMN IF NOT EXISTS sport VARCHAR(20) DEFAULT 'cricket';
UPDATE leagues SET sport = 'cricket' WHERE sport IS NULL;
