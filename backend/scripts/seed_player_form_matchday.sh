#!/usr/bin/env bash
# seed_player_form_matchday.sh
#
# Seeds player form data locally for teams playing in the next N days,
# then exports and applies it to production.
#
# Usage:
#   ./scripts/seed_player_form_matchday.sh <days_ahead> <prod_user@prod_host> <prod_db_url>
#
# Examples:
#   ./scripts/seed_player_form_matchday.sh 1 root@139.59.3.190 "postgresql://lazy_fantasy_db_admin:RKD#bd123@localhost:5432/lazy_fantasy_league"
#   ./scripts/seed_player_form_matchday.sh 4 root@139.59.3.190 "postgresql://lazy_fantasy_db_admin:RKD#bd123@localhost:5432/lazy_fantasy_league"
#
# Prerequisites:
#   - Local docker-compose stack running (make up)
#   - Backend running at localhost:8000
#   - SSH key access to prod host
#   - ADMIN_EMAIL / ADMIN_PASS env vars set, or edit defaults below

set -euo pipefail

# ── Config ─────────────────────────────────────────────────────────────────────
DAYS_AHEAD="${1:?Usage: $0 <days_ahead> <prod_user@prod_host> <prod_db_url>}"
PROD_HOST="${2:?Usage: $0 <days_ahead> <prod_user@prod_host> <prod_db_url>}"
PROD_DB_URL="${3:?Usage: $0 <days_ahead> <prod_user@prod_host> <prod_db_url>}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
ADMIN_EMAIL="${ADMIN_EMAIL:-yugoja20@gmail.com}"
ADMIN_PASS="${ADMIN_PASS:-devpass}"
LOCAL_SQL="/tmp/player_form_matchday.sql"
PROD_SQL="/tmp/player_form_matchday.sql"

# ── Step 1: Get admin token ────────────────────────────────────────────────────
echo "→ Authenticating..."
TOKEN=$(curl -sf -X POST "$BACKEND_URL/auth/login" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d "username=${ADMIN_EMAIL}&password=${ADMIN_PASS}" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

if [[ -z "$TOKEN" ]]; then
  echo "✗ Failed to get admin token. Is the local backend running?"
  exit 1
fi
echo "  ✓ Token obtained"

# ── Step 2: Trigger seed ───────────────────────────────────────────────────────
echo "→ Triggering seed for teams with matches in next ${DAYS_AHEAD} day(s)..."
RESPONSE=$(curl -sf -X POST "$BACKEND_URL/admin/wc/seed-player-form" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"wc_league_id\": 1, \"season\": 2026, \"days_ahead\": ${DAYS_AHEAD}}")
echo "  ✓ Seed started: $RESPONSE"

# ── Step 3: Wait for completion ────────────────────────────────────────────────
echo "→ Waiting for seed to complete (polling logs every 10s)..."
ATTEMPTS=0
MAX_ATTEMPTS=90  # 15 minutes max
until docker logs lazyfantasy-backend 2>&1 | grep -q "seed-player-form complete"; do
  ATTEMPTS=$((ATTEMPTS + 1))
  if [[ $ATTEMPTS -ge $MAX_ATTEMPTS ]]; then
    echo "✗ Timed out waiting for seed. Check docker logs lazyfantasy-backend"
    exit 1
  fi
  sleep 10
  echo "  ... still running (${ATTEMPTS}/${MAX_ATTEMPTS})"
done

COMPLETION=$(docker logs lazyfantasy-backend 2>&1 | grep "seed-player-form complete" | tail -1)
echo "  ✓ $COMPLETION"

# ── Early exit if all 48 teams are now covered ─────────────────────────────────
if echo "$COMPLETION" | grep -q "all_covered=True"; then
  echo ""
  echo "🎉 All teams covered — no more seeding needed!"
  echo "   You can stop running this script for future match days."
  # Still export and push so prod has the latest data
fi

# ── Step 4: Generate SQL dump (name-based, safe for prod) ─────────────────────
echo "→ Generating SQL dump..."
docker exec lazyfantasy-db psql -U lazyfantasy -d lazyfantasy_dev -t -A -c "
SELECT
  'INSERT INTO player_form (player_id, expected_points, floor, availability, wc_goals, wc_assists, wc_minutes, wc_clean_sheets, wc_games, pre_expected_points)'
  || ' SELECT p.id, '
  || pf.expected_points || ', '
  || quote_literal(pf.floor) || ', '
  || quote_literal(pf.availability) || ', '
  || pf.wc_goals || ', '
  || pf.wc_assists || ', '
  || pf.wc_minutes || ', '
  || pf.wc_clean_sheets || ', '
  || pf.wc_games || ', '
  || COALESCE(pf.pre_expected_points::text, 'NULL')
  || ' FROM players p JOIN teams t ON p.team_id = t.id'
  || ' WHERE p.name = ' || quote_literal(pl.name)
  || ' AND t.name = ' || quote_literal(tm.name)
  || ' AND t.sport = ''football'''
  || ' ON CONFLICT (player_id) DO UPDATE SET'
  || ' expected_points=EXCLUDED.expected_points,'
  || ' pre_expected_points=EXCLUDED.pre_expected_points,'
  || ' floor=EXCLUDED.floor,'
  || ' availability=EXCLUDED.availability;'
FROM player_form pf
JOIN players pl ON pf.player_id = pl.id
JOIN teams tm ON pl.team_id = tm.id
" > "$LOCAL_SQL"

# Append team api_football_team_id updates
docker exec lazyfantasy-db psql -U lazyfantasy -d lazyfantasy_dev -t -A -c "
SELECT 'UPDATE teams SET api_football_team_id=' || quote_literal(api_football_team_id)
  || ' WHERE name=' || quote_literal(name) || ' AND sport=''football'';'
FROM teams
WHERE sport = 'football' AND api_football_team_id IS NOT NULL;
" >> "$LOCAL_SQL"

ROWS=$(wc -l < "$LOCAL_SQL")
echo "  ✓ ${ROWS} SQL statements written to $LOCAL_SQL"

# ── Step 5: Copy to prod ───────────────────────────────────────────────────────
echo "→ Copying SQL to $PROD_HOST..."
scp "$LOCAL_SQL" "${PROD_HOST}:${PROD_SQL}"
echo "  ✓ Copied"

# ── Step 6: Apply on prod ──────────────────────────────────────────────────────
echo "→ Applying on prod..."
# Pass DB URL via PGPASSWORD + individual params to avoid # in password breaking shell
ssh "$PROD_HOST" "psql '${PROD_DB_URL}' -f ${PROD_SQL} -v ON_ERROR_STOP=0 2>&1 | tail -5"
echo "  ✓ Done"

echo ""
echo "✅ Match day seed complete for days_ahead=${DAYS_AHEAD}"
echo "   Re-run anytime — all statements are idempotent upserts."
