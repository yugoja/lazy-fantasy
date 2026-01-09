# Project Specification: Fantasy Cricket League (MVP)

## 1. Overview
A backend-focused fantasy cricket application where users form private groups (leagues), predict daily match outcomes for specific tournaments (e.g., IPL, World Cup), and compete on a group leaderboard.

## 2. Tech Stack
- **Language:** Python 3.10+
- **Framework:** FastAPI
- **Database:** SQLite (using SQLAlchemy ORM or SQLModel)
- **Authentication:** OAuth2 with Password (JWT tokens)
- **Validation:** Pydantic schema validation

## 3. Data Model (Schema)

### Users
- `id`: Integer, Primary Key
- `username`: String, Unique
- `email`: String, Unique
- `hashed_password`: String

### Leagues (Groups)
- `id`: Integer, Primary Key
- `name`: String
- `invite_code`: String, Unique (6-char alphanumeric)
- `owner_id`: ForeignKey(Users.id)

### LeagueMembers
- Link table between Users and Leagues (Many-to-Many)
- `league_id`: ForeignKey
- `user_id`: ForeignKey

### Tournaments
- `id`: Integer, Primary Key
- `name`: String (e.g., "IPL 2025")
- `start_date`: Date
- `end_date`: Date

### Teams
- `id`: Integer, Primary Key
- `name`: String (e.g., "India", "Australia")
- `short_name`: String (e.g., "IND", "AUS")
- `logo_url`: String (Optional)

### Players
- `id`: Integer, Primary Key
- `name`: String
- `team_id`: ForeignKey(Teams.id)
- `role`: String (Batsman, Bowler, All-Rounder, Wicketkeeper)

### Matches
- `id`: Integer, Primary Key
- `tournament_id`: ForeignKey(Tournaments.id)
- `team_1_id`: ForeignKey(Teams.id)
- `team_2_id`: ForeignKey(Teams.id)
- `start_time`: Datetime (UTC)
- `status`: Enum (SCHEDULED, COMPLETED)
- `result_winner_id`: ForeignKey(Teams.id), Nullable
- `result_most_runs_player_id`: ForeignKey(Players.id), Nullable
- `result_most_wickets_player_id`: ForeignKey(Players.id), Nullable
- `result_pom_player_id`: ForeignKey(Players.id), Nullable

### Predictions
- `id`: Integer, Primary Key
- `user_id`: ForeignKey(Users.id)
- `match_id`: ForeignKey(Matches.id)
- `predicted_winner_id`: ForeignKey(Teams.id)
- `predicted_most_runs_player_id`: ForeignKey(Players.id)
- `predicted_most_wickets_player_id`: ForeignKey(Players.id)
- `predicted_pom_player_id`: ForeignKey(Players.id)
- `points_earned`: Integer (Default 0)
- `is_processed`: Boolean (Default False)

## 4. Business Rules & Logic

### A. Prediction Constraints
1. **Deadline:** Users can create or update predictions ONLY if `current_time (UTC) < match.start_time (UTC)`.
2. **Team Validation:** The predicted players must belong to one of the two teams playing in that match.

### B. Scoring System (Triggered automatically on Match Completion)
When a match status changes to `COMPLETED` and results are entered:
1. **Winner Prediction:** +10 pts if correct.
2. **Most Runs:** +20 pts if correct. (If multiple players tied for most runs, all valid predictions get points).
3. **Most Wickets:** +20 pts if correct. (Same tie logic).
4. **Player of Match:** +50 pts if correct.
5. **DNP (Did Not Play):** 0 pts if the predicted player was not in the final XI.

### C. Leaderboard
- Leaderboard is calculated by summing `Predictions.points_earned` for all users within a specific `League`.

## 5. API Endpoints (Core MVP)

### Auth
- `POST /auth/signup`: Register new user.
- `POST /auth/login`: Get JWT token.

### Leagues
- `POST /leagues/`: Create a new league (generates invite code).
- `POST /leagues/join`: Join league using invite code.
- `GET /leagues/{id}/leaderboard`: Get list of members sorted by total score.

### Matches & Data
- `GET /matches/`: List upcoming matches (Optional filter: `?tournament_id=1`).
- `GET /matches/{id}/players`: Get all players from both teams (for dropdowns).

### Predictions
- `POST /predictions/`: Submit prediction (payload: match_id, winner_id, bat_id, bowl_id, pom_id).
- `GET /predictions/my`: See my history.

### Admin (Manual Data Entry)
- `POST /admin/matches/`: Create a match.
- `POST /admin/matches/{id}/result`: Set match results (Winner, Best Bat, Best Bowl, POM).
  - **Action:** This endpoint must trigger the `calculate_scores(match_id)` service function.

## 6. Non-Functional & Dev Requirements

### A. Data Seeding
- Create a script `seed.py` that reads a JSON file (e.g., `initial_data.json`).
- This script must pre-populate:
  - 1 Tournament (e.g., "World Cup 2025")
  - 2 Teams with ~15 players each.
  - 1 Upcoming Match.
- *Reason:* Facilitates easy database reset and testing.

### B. Timezone Handling
- All timestamps in the Database must be stored in **UTC**.
- API responses must return UTC ISO strings (e.g., `2025-06-01T14:00:00Z`).
- The Frontend is responsible for converting UTC to local user time.

### C. CORS Configuration
- Configure FastAPI CORS middleware to allow requests from `localhost:3000` (React/Next.js default port) or `*` for development.
- Allow headers: `Authorization`, `Content-Type`.