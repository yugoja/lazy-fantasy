# Lazy Fantasy - Project Context

## Architecture
- **Frontend**: Next.js 16 + TypeScript + Tailwind + shadcn/ui (`frontend/`)
- **Backend**: FastAPI + SQLAlchemy + SQLite + JWT auth (`backend/`)
- **Branch**: `feature/v0-redesign` (active development)

## Pending TODO

### Testing
- [x] Run existing backend tests (`backend/tests/`) and verify they pass with current changes
  - `tests/unit/test_auth.py`
  - `tests/unit/test_scoring.py`
  - `tests/integration/test_tournament_flow.py`
  - Run with: `cd backend && source venv/bin/activate && pytest`
- [x] Set up frontend testing infrastructure (Vitest + @testing-library/react)
  - Vitest 4 + happy-dom + @testing-library/react configured
  - Run with: `cd frontend && npm run test:run`
- [x] Write frontend tests for key flows:
  - Login/signup form submission
  - Prediction form pre-fill and submit
  - MatchCard rendering with/without `hasPredicted`
  - 401 interceptor redirect behavior in `lib/api.ts`
  - Leaderboard league selector and data loading

### Minor Code Quality Fixes
- [x] Add `aria-label="Copy invite code"` to icon-only copy button in `frontend/src/app/leagues/page.tsx`
- [x] Replace `console.error` with proper error state in:
  - `frontend/src/app/predictions/page.tsx`
  - `frontend/src/app/leagues/page.tsx`

### Production Readiness
- [x] Ensure backend `.env` sets `SECRET_KEY`, `CORS_ORIGINS`, `DATABASE_URL` for production
  - `.env.example` documents all variables; `config.py` emits a warning if `SECRET_KEY` is the insecure default
- [x] Ensure frontend `.env.local` sets `NEXT_PUBLIC_API_URL` for production
  - `.env.example` documents the variable with production comment
- [x] Consider adding structured error tracking (e.g., Sentry)
  - Sentry integrated in both backend (FastAPI) and frontend (Next.js)
  - Opt-in via `SENTRY_DSN` / `NEXT_PUBLIC_SENTRY_DSN` env vars

## Completed (Phase 4 - commit 357711f)
- Redesigned all pages with shadcn/ui + Tailwind (login, signup, landing, admin, set result, view predictions)
- Created profile page (`/profile`)
- Deleted all CSS modules and dead Navbar component
- Fixed JWT token expiry (30min -> 7 days)
- Added 401 interceptor with redirect to login
- Pre-fill prediction form for existing predictions
- MatchCard `hasPredicted` prop with "Update Prediction" CTA
- Replaced hardcoded leaderboard with real API data
- Removed fake dashboard stats, unused maxMembers state
- Fixed broken nav links (View Live, predict back, profile leagues)
- Added error display on matches page
- Added onError fallback on all flag images
- Yellow countdown pill on MatchCard
