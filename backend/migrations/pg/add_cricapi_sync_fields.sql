-- Add CricAPI sync fields to matches table (PostgreSQL).
-- Run: psql $DATABASE_URL -f migrations/pg/add_cricapi_sync_fields.sql

ALTER TABLE matches ADD COLUMN IF NOT EXISTS external_match_id VARCHAR(100);
ALTER TABLE matches ADD COLUMN IF NOT EXISTS sync_state VARCHAR(20) DEFAULT 'unlinked';
ALTER TABLE matches ADD COLUMN IF NOT EXISTS sync_error VARCHAR(500);
ALTER TABLE matches ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMP WITH TIME ZONE;
