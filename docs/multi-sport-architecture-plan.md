# Multi-Sport Architecture: Adding Football World Cup Alongside IPL 2026

## Context

Lazy Fantasy ships today as a cricket-only product. IPL 2026 is wired into the schema, scoring, prediction UI, and admin flows. The goal is to add the upcoming football World Cup as a second tournament that runs alongside IPL — and to do it in a way that makes a 3rd, 4th, 5th sport a known quantity rather than a rewrite.

What's already friendly to multi-sport:
- `tournament.sport`, `team.sport`, `league.sport` columns already exist (default `'cricket'`).
- `Match`, `League`, `LeagueMember`, `Leaderboard`, `MatchCard`, `OnboardingChecklist`, reminders/notifications, push subscriptions, and the rank-snapshot pipeline are sport-agnostic.
- Frontend `League` type carries `sport?: string`; `createLeague(name, sport)` already accepts a sport arg.

What's hard-coupled to cricket (the work):
- `Prediction` table has 6 cricket-shaped FK columns; same for `Match` result fields (6 result FKs).
- `app/services/scoring.py` hardcodes 6 hit categories and their point values.
- `app/routers/prediction.py` and Pydantic schemas validate the 6 cricket fields directly.
- `frontend/src/app/matches/[id]/predict/page.tsx` is a 6-step cricket form with role filtering (`isBatter`, `isBowler`) and "Top Batsman / Top Bowler / POM" labels.
- `frontend/src/app/predictions/page.tsx` (Done tab) hardcodes the 6 cricket categories with their icons and point values.
- `frontend/src/app/admin/matches/[id]/result/page.tsx` collects the 6 cricket result fields.
- `DugoutFeed.tsx` hardcodes `agreement_count}/6` (the cricket category count) and uses cricket-tinted copy.

The football World Cup launches with **match-level predictions only** — no tournament-level mega picks (Top-4 / Golden Boot) at launch. Per-match picks are:
- **Winner (with draw)** — group-stage matches can draw; backend stores nullable `winner_id` + `is_draw` flag.
- **Exact scoreline** — `team1_goals` + `team2_goals`.
- **Man of the Match** — single player from either squad.

## Recommended architecture: polymorphic sport tables

Keep a thin shared `predictions` row (id, user_id, match_id, points_earned, is_processed) and split sport-specific columns into 1:1 child tables joined by FK. Same shape for match results.

```
predictions (shared)
  ├── cricket_predictions   (prediction_id PK/FK + 6 cricket FKs)
  └── football_predictions  (prediction_id PK/FK + winner_id nullable,
                             is_draw, team1_goals, team2_goals, motm_player_id)

match_results (or kept inline on match for now)
  ├── cricket_match_results
  └── football_match_results
```

Rationale (full discussion in conversation): preserves FK integrity to `teams`/`players`, keeps sport-specific NOT NULLs where they matter, makes scoring a 3-line dispatcher instead of an `if sport ==` cascade, and the eventual escape hatch to a generic EAV table at sport #6+ is a clean per-sport migration because the boundaries are already drawn at the service layer.

For the **Match result** fields, two viable shapes:
1. Keep the 6 cricket fields on `match` for now, add a sibling `football_match_results` 1:1 table. Less migration churn.
2. Split symmetrically into `cricket_match_results` + `football_match_results`, leaving `match` slim.

**Recommend option 2** for symmetry with predictions and to keep `match` agnostic. The cricket data migration is the same one-time script either way.

## Backend changes

### Models — `backend/app/models/`
- `prediction.py`: strip cricket FKs from `Prediction`. Add `CricketPrediction` (1:1, holds the existing 6 FKs) and `FootballPrediction` (1:1, holds winner_id nullable + is_draw + team1_goals + team2_goals + motm_player_id). Use SQLAlchemy 1:1 `relationship(uselist=False)` from `Prediction` to each child; sport is resolved via `match.tournament.sport`.
- `match.py`: strip the 6 `result_*` cricket columns. Add `CricketMatchResult` and `FootballMatchResult` models in new files under `models/`.
- No changes to `Tournament`, `Team`, `League`, `Player`, `LeagueMember`, `DugoutDismissal`, `ReminderLog`, `PushSubscription`, `MatchLineup`. `Player.role` stays a free-form string ("Goalkeeper", "Defender", "Midfielder", "Forward" for football).

### Schemas — `backend/app/schemas/`
- `prediction.py`: introduce `CricketPredictionPayload` and `FootballPredictionPayload` (Pydantic). `PredictionCreate` becomes a discriminated union on `sport`, or a sport-tagged envelope: `{sport: 'cricket' | 'football', payload: {...}}`. The router resolves which payload to expect from `match.tournament.sport`.
- `match.py`: similar discriminated-union treatment for `MatchResultCreate`.

### Scoring — `backend/app/services/`
- Rename existing `scoring.py` → `scoring_cricket.py` (keep the 6-hit logic and `_CATEGORY_POINTS` map intact; just rebind from `prediction.predicted_*` to `prediction.cricket.predicted_*`).
- New `scoring_football.py` with `compute_hits(football_pred, football_result) -> dict[str, bool]` and a category map. Suggested starting points (tunable, mirrors cricket's 140-pt ceiling so cross-sport leaderboards stay normalized):
  - `winner`: 20 pts (harder than cricket — draws are real)
  - `scoreline`: 70 pts (rare hit, big payoff)
  - `motm`: 50 pts
  - max per match: 140
- New `scoring.py` thin dispatcher: `calculate_scores(db, match_id)` reads `match.tournament.sport` and delegates to the right module. Public signature unchanged so routers/admin code don't move.

### Routers — `backend/app/routers/`
- `prediction.py`: `POST /predictions/` validates sport-shaped payload and writes both `Prediction` + the sport child row in one transaction. `GET /predictions/my/detailed` returns sport-tagged objects so the frontend can render the correct component.
- `admin.py`: `POST /admin/matches/{id}/result` accepts sport-shaped result body; creates the appropriate `*MatchResult` row; the rest of the flow (`reset is_processed`, snapshot ranks, call `calculate_scores`) is unchanged.

### Dugout — `backend/app/services/dugout.py`
- The `agreement` event currently assumes 6 categories. Genericize: read the category count from the sport's scoring module (`scoring_cricket.CATEGORY_COUNT = 6`, `scoring_football.CATEGORY_COUNT = 3`) and emit it on the event payload so the frontend can render `N/M` correctly.
- "Contrarian" event copy is sport-tinted; pass sport on the event so the frontend can swap labels (e.g. "lone wolf on the scoreline" vs "lone wolf on POM").

### Migrations — `backend/migrations/pg/`
Single new migration (`006_polymorphic_predictions.sql` or similar):
1. `CREATE TABLE cricket_predictions` with the 6 existing FK columns + `prediction_id` PK/FK to `predictions`.
2. `INSERT INTO cricket_predictions SELECT id, predicted_winner_id, ... FROM predictions WHERE <those cols are not null>`.
3. `ALTER TABLE predictions DROP COLUMN predicted_winner_id, ...` (the 6 cricket cols).
4. `CREATE TABLE football_predictions` (empty).
5. Repeat the same three steps for `match` → `cricket_match_results` and `football_match_results`.

Wrap in a transaction. Test on a prod dump locally before running on the droplet.

### Tests — `backend/tests/`
- `unit/test_scoring.py`: split into `test_scoring_cricket.py` (existing) + new `test_scoring_football.py`. Both call the dispatcher to assert routing too.
- `integration/test_tournament_flow.py`: this test asserts cricket-shaped max 140 points (line ~198 per the earlier exploration). Parameterize or add a parallel `test_football_tournament_flow.py` that walks the football flow end-to-end (sign-up → join football league → predict → admin sets result → leaderboard reflects points).
- `integration/test_admin_sync.py`: stays cricket; CricAPI is cricket-only. Note that football won't have a sync provider at launch — admin enters results manually.
- `integration/test_dugout_flow.py`: update `agreement_count/6` assumption to be sport-aware.

## Frontend changes

### Types — `frontend/src/types/index.ts`
- Split `Prediction` into a tagged union: `CricketPrediction` (existing shape) and `FootballPrediction` (winner_id nullable, is_draw, team1_goals, team2_goals, motm_player_id). Common parent has `points_earned`, `is_processed`, `sport`, match info.
- Same treatment for `MatchResult`.

### Prediction form — `frontend/src/app/matches/[id]/predict/page.tsx`
- Split this 600-line cricket-shaped page into a thin router + per-sport step flows:
  - `frontend/src/app/matches/[id]/predict/page.tsx` — fetches match, reads `match.tournament.sport`, renders one of:
  - `frontend/src/components/predict/CricketPredictFlow.tsx` — current 6 steps lifted as-is.
  - `frontend/src/components/predict/FootballPredictFlow.tsx` — 3 steps: Winner (3 buttons: team1 / draw / team2), Scoreline (two number steppers, capped at e.g. 9), MOTM (single player picker, both squads pooled).
- Reuse the existing step-card chrome, progress bar, and submit-confirmation animation. Reuse `TeamFormEntry` for football's last-5 form (W/D/L instead of W/L/NR).

### Done tab — `frontend/src/app/predictions/page.tsx`
- The hardcoded 6-category array (`Winner / Runs ×2 / Wkts ×2 / POM`) becomes a sport-dispatched array sourced from a small frontend constants file `frontend/src/lib/scoring.ts` that mirrors the backend `CATEGORY_POINTS` maps per sport.
- Per-category progress bars and accuracy bars on the summary card render whatever categories the sport defines.
- Share text: `🏏` emoji becomes `⚽` for football matches; copy template is parameterized.

### Admin set-result — `frontend/src/app/admin/matches/[id]/result/page.tsx`
- Same router pattern as the prediction form: read sport, render `CricketResultForm` (current 6 dropdowns) or `FootballResultForm` (winner/draw radio, two score steppers, MOTM dropdown).

### Dugout — `frontend/src/components/DugoutFeed.tsx`
- Replace hardcoded `agreement_count}/6` with `agreement_count}/{event.category_count}` (now emitted by backend).
- Sport-tinted strings (icons, copy) read from a small per-sport copy map.

### Sport-agnostic, no changes needed
- `MatchCard.tsx`, `OnboardingChecklist.tsx`, `StatsOverview.tsx`, league pages, leaderboard, profile, login/signup, push-subscription UI, reminders.

## Seeding & operational work

- **Football tournament row**: insert one `Tournament` row with `sport='football'`, World Cup start/end dates, picks window = `'open'`.
- **Teams**: ~32 World Cup teams seeded with `sport='football'`. New script `backend/scripts/seed_worldcup_teams.py` modeled on `seed_ipl2026_fixtures.py`.
- **Players**: 23–26 squad members per team (~700–800 rows). Script `backend/scripts/seed_worldcup_squads.py`. Role strings: `Goalkeeper`, `Defender`, `Midfielder`, `Forward`.
- **Fixtures**: 64 World Cup matches seeded with kickoffs in UTC. Same pattern as `seed_ipl2026_fixtures.py`.
- **CricAPI sync stays cricket-only**: no provider integration for football at launch; admin enters results manually via the football result form. `match.external_match_id` and `sync_state` columns simply stay null for football matches.
- **Reminders**: zero changes — the 55–65 minute window in `app/services/scheduler.py:_send_match_reminders()` is sport-agnostic. Push payload template ("⏰ {team_1} vs {team_2} in 1 hour!") works as-is.
- **Leaderboard**: zero changes — points sum across all predictions regardless of sport. Cross-sport leaderboards work for free if a league's sport is set to something neutral; per-sport leagues remain filtered by `league.sport`.

## Open decisions to confirm before/during implementation

1. **Football point values**: starting suggestion is 20 / 70 / 50 = 140 to match cricket's ceiling so cross-sport leaderboards stay normalized. Worth one tuning pass once the UX is real.
2. **Sport-mixed leagues**: today `League.sport` is set at creation. Do football matches show up in a `sport='cricket'` league? Recommend: a league is single-sport (current behavior), and users join a separate football league. Cleaner social dynamics and matches the "World Cup pool with friends" mental model.
3. **Sport selector at signup / dashboard**: with two sports running concurrently, the dashboard needs a way to show both sets of matches or let the user pick. Simplest: dashboard lists all `SCHEDULED` matches across both sports the user has at least one league for; each `MatchCard` already shows team names with no cricket assumption.

## Out of scope for this launch

- Football tournament-level mega picks (Top-4 + Golden Boot + Golden Glove). Defer to a follow-up; the polymorphic pattern applied to `TournamentPick` is the same template as predictions.
- Live data sync for football (no FootballAPI integration). Admin enters results manually.
- Knockout-stage extra pick categories (penalty shootout winner, extra-time goalscorer). The Football flow has 3 picks at launch; extras can be added as future fields on `football_predictions` / `football_match_results` without further structural change.

## Critical files to modify

Backend:
- `backend/app/models/prediction.py` (split)
- `backend/app/models/match.py` (drop result columns; add 2 result models in new files)
- `backend/app/schemas/prediction.py`, `backend/app/schemas/match.py` (discriminated unions)
- `backend/app/services/scoring.py` (becomes dispatcher) + new `scoring_cricket.py`, `scoring_football.py`
- `backend/app/services/dugout.py` (genericize agreement count + sport on events)
- `backend/app/routers/prediction.py`, `backend/app/routers/admin.py`
- `backend/migrations/pg/006_polymorphic_predictions.sql` (new)
- `backend/scripts/seed_worldcup_teams.py`, `seed_worldcup_squads.py`, `seed_worldcup_fixtures.py` (new)

Frontend:
- `frontend/src/types/index.ts` (tagged unions)
- `frontend/src/app/matches/[id]/predict/page.tsx` (sport router)
- `frontend/src/components/predict/CricketPredictFlow.tsx`, `FootballPredictFlow.tsx` (new)
- `frontend/src/app/predictions/page.tsx` (sport-aware Done tab)
- `frontend/src/app/admin/matches/[id]/result/page.tsx` (sport router) + `CricketResultForm`, `FootballResultForm` components
- `frontend/src/components/DugoutFeed.tsx` (denominator + copy)
- `frontend/src/lib/scoring.ts` (new — per-sport category constants)

## Verification plan

1. **Backend unit**: `cd backend && source venv/bin/activate && pytest tests/unit/` — both cricket and football scoring suites green.
2. **Backend integration**: `pytest tests/integration/` — existing cricket flow still passes; new football flow asserts predict → set-result → leaderboard end-to-end.
3. **Migration**: run `006_polymorphic_predictions.sql` against a local Postgres restored from a prod dump. Verify row counts: `SELECT COUNT(*) FROM cricket_predictions` equals pre-migration `predictions` count. Spot-check a handful of users' points are unchanged.
4. **Frontend manual QA in browser**:
   - Cricket league: predict a match (6 steps), submit, confirm summary, view Done tab — unchanged from today.
   - Football league: predict a match (3 steps), pick a draw, submit, view Done tab — football icons and category labels appear correctly.
   - Admin: set result for one cricket match and one football match; verify points compute correctly in both.
   - Dugout: trigger an agreement event in both sports, verify `N/6` and `N/3` denominators render.
5. **Reminders**: enable a test match 60 minutes in the future for each sport; confirm one push fires per match (no regression for cricket).
