-- Add CricAPI sync fields to matches table.
-- Run: sqlite3 fantasy_cricket.db < migrations/add_cricapi_sync_fields.sql

ALTER TABLE matches ADD COLUMN external_match_id VARCHAR(100);
ALTER TABLE matches ADD COLUMN sync_state VARCHAR(20) DEFAULT 'unlinked';
ALTER TABLE matches ADD COLUMN sync_error VARCHAR(500);
ALTER TABLE matches ADD COLUMN last_synced_at DATETIME;
