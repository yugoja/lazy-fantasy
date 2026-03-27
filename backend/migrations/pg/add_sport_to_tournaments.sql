-- Add sport column to tournaments table (PostgreSQL).
-- Run: psql $DATABASE_URL -f migrations/pg/add_sport_to_tournaments.sql

ALTER TABLE tournaments ADD COLUMN IF NOT EXISTS sport VARCHAR(20) DEFAULT 'cricket';
UPDATE tournaments SET sport = 'cricket' WHERE sport IS NULL;
