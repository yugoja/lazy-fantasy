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

### Features
- [ ] Match reminders — email or push notifications before matches lock (built, needs RESEND_API_KEY + VAPID keys on droplet)
- [ ] Update app icon — replace existing icons in `frontend/public/icons/` (192×192 and 512×512 PNG) and `frontend/public/icons/icon-192x192.png` used as Apple touch icon in `layout.tsx`
- [x] PWA support — add a manifest so users can "install" it on mobile
  - `manifest.json` with app name, icons, standalone display, dark theme
  - Minimal service worker (`sw.js`) satisfies Chrome install requirement
  - Apple Web App meta tags for iOS "Add to Home Screen"
  - 192x192 and 512x512 icons generated from `logo.png`
- [x] Image optimization — flag images served through Next.js `<Image>` with proper caching
  - All 9 `<img>` tags replaced with `next/image` `<Image>` across 5 files
  - Automatic lazy loading, WebP/AVIF conversion, and CLS prevention via explicit width/height
- [x] Google SSO — login using Google single sign-on
  - Backend: `google-auth` verifies ID token at `/auth/google`, finds/creates user, returns JWT
  - Frontend: Google Identity Services button on login/signup, graceful degradation when `GOOGLE_CLIENT_ID` not set
  - Opt-in via `GOOGLE_CLIENT_ID` (backend) / `NEXT_PUBLIC_GOOGLE_CLIENT_ID` (frontend)

### Engagement & Social
- [ ] Social nudge — prompt users to challenge friends after a match result drops
- [ ] Prediction streak display — make streak more prominent/celebratory on dashboard and profile to drive daily engagement
- [ ] WhatsApp score share improvements — richer message copy, share from leaderboard view, share after result first loads (not just on Done tab)
- [ ] Pre-match banter — show aggregate predictions (e.g. "60% of your league picked India") after predictions lock

### UX Improvements
- [x] Onboarding flow — 3-step checklist card on dashboard (predict, join league, enable notifications); auto-completes, dismissible via localStorage
- [x] Signup redirects to /predictions instead of /dashboard for new users
- [x] Prediction confirmation — animated pulsing icon + summary card showing all 4 picks with points earned + "Up to 100 pts" total
- [x] Done tab enhancements — show points breakdown more visually (progress bars, correct/wrong counts per category)
  - Summary card: total points progress bar, per-category accuracy bars (Winner/Runs/Wickets/POM), overall accuracy count
  - Per-prediction cards: points earned shown next to each correct category

### League Features
- [ ] League activity feed — see what others predicted after the match locks
- [ ] Head-to-head — compare your predictions vs a specific friend in a league
- [ ] Mini leaderboard on match card — show user's current rank in context while predicting
- [ ] Leaderboard rank history in DB — currently tracked in localStorage (resets on new device/browser); persist rank snapshots in backend after each match result so deltas are accurate across devices

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
