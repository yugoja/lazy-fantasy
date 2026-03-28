-- Migration: Add tournament picks feature (PostgreSQL)
-- Picks window state on tournament
ALTER TABLE tournaments ADD COLUMN IF NOT EXISTS picks_window VARCHAR(10) NOT NULL DEFAULT 'closed';

-- Tournament result columns
ALTER TABLE tournaments ADD COLUMN IF NOT EXISTS result_top4_team1_id INTEGER REFERENCES teams(id);
ALTER TABLE tournaments ADD COLUMN IF NOT EXISTS result_top4_team2_id INTEGER REFERENCES teams(id);
ALTER TABLE tournaments ADD COLUMN IF NOT EXISTS result_top4_team3_id INTEGER REFERENCES teams(id);
ALTER TABLE tournaments ADD COLUMN IF NOT EXISTS result_top4_team4_id INTEGER REFERENCES teams(id);
ALTER TABLE tournaments ADD COLUMN IF NOT EXISTS result_best_batsman_player_id INTEGER REFERENCES players(id);
ALTER TABLE tournaments ADD COLUMN IF NOT EXISTS result_best_bowler_player_id INTEGER REFERENCES players(id);

-- Tournament picks table
CREATE TABLE IF NOT EXISTS tournament_picks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    tournament_id INTEGER NOT NULL REFERENCES tournaments(id),
    top4_team1_id INTEGER REFERENCES teams(id),
    top4_team2_id INTEGER REFERENCES teams(id),
    top4_team3_id INTEGER REFERENCES teams(id),
    top4_team4_id INTEGER REFERENCES teams(id),
    best_batsman_player_id INTEGER REFERENCES players(id),
    best_bowler_player_id INTEGER REFERENCES players(id),
    points_earned INTEGER NOT NULL DEFAULT 0,
    is_window2 BOOLEAN NOT NULL DEFAULT FALSE,
    is_processed BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE(user_id, tournament_id)
);
