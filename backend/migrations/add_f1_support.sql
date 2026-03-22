-- Migration: Add F1 support to Lazy Fantasy
-- Run against production PostgreSQL database

-- 1. Add sport column to existing tables
ALTER TABLE tournaments ADD COLUMN sport VARCHAR(20) NOT NULL DEFAULT 'cricket';
ALTER TABLE leagues ADD COLUMN sport VARCHAR(20) NOT NULL DEFAULT 'cricket';
ALTER TABLE teams ADD COLUMN sport VARCHAR(20) NOT NULL DEFAULT 'cricket';

-- 2. Create F1 races table
CREATE TABLE f1_races (
    id SERIAL PRIMARY KEY,
    tournament_id INTEGER NOT NULL REFERENCES tournaments(id),
    name VARCHAR(100) NOT NULL,
    circuit VARCHAR(200) NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(9) NOT NULL DEFAULT 'SCHEDULED',
    result_p1_driver_id INTEGER REFERENCES players(id),
    result_p2_driver_id INTEGER REFERENCES players(id),
    result_p3_driver_id INTEGER REFERENCES players(id),
    result_fastest_lap_driver_id INTEGER REFERENCES players(id),
    result_biggest_mover_driver_id INTEGER REFERENCES players(id),
    result_safety_car BOOLEAN
);
CREATE INDEX ix_f1_races_id ON f1_races(id);

-- 3. Create F1 predictions table
CREATE TABLE f1_predictions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    race_id INTEGER NOT NULL REFERENCES f1_races(id),
    predicted_p1_driver_id INTEGER NOT NULL REFERENCES players(id),
    predicted_p2_driver_id INTEGER NOT NULL REFERENCES players(id),
    predicted_p3_driver_id INTEGER NOT NULL REFERENCES players(id),
    predicted_fastest_lap_driver_id INTEGER NOT NULL REFERENCES players(id),
    predicted_biggest_mover_driver_id INTEGER NOT NULL REFERENCES players(id),
    predicted_safety_car BOOLEAN NOT NULL,
    points_earned INTEGER NOT NULL DEFAULT 0,
    is_processed BOOLEAN NOT NULL DEFAULT FALSE,
    points_podium INTEGER NOT NULL DEFAULT 0,
    points_fastest_lap INTEGER NOT NULL DEFAULT 0,
    points_biggest_mover INTEGER NOT NULL DEFAULT 0,
    points_safety_car INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX ix_f1_predictions_id ON f1_predictions(id);
