-- Add prev_rank column to league_members to support leaderboard rank delta display.
-- Run on production: psql $DATABASE_URL -f migrations/add_prev_rank_to_league_members.sql
ALTER TABLE league_members ADD COLUMN IF NOT EXISTS prev_rank INTEGER;
