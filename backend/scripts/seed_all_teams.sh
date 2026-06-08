#!/usr/bin/env bash
# seed_all_teams.sh
#
# Seeds player form data for all 48 WC teams one at a time, then exports
# the full player_form table and applies it to production.
#
# Usage:
#   ./scripts/seed_all_teams.sh <prod_user@prod_host> "<prod_db_url>"
#
# Examples:
#   ./scripts/seed_all_teams.sh root@139.59.3.190 "postgresql://lazy_fantasy_db_admin:RKD#bd123@localhost:5432/lazy_fantasy_league"
#
# The script skips teams that are already seeded (skip_seeded=true is the default).
# Once all_covered=True appears in the log, it exports and pushes to prod.
#
# Prerequisites:
#   - Local docker-compose stack running (make up)
#   - Backend running at localhost:8000
#   - SSH key access to prod host
#   - ADMIN_EMAIL / ADMIN_PASS env vars set, or edit defaults below

set -euo pipefail

# ── Config ─────────────────────────────────────────────────────────────────────
PROD_HOST="${1:?Usage: $0 <prod_user@prod_host> <prod_db_url>}"
PROD_DB_URL="${2:?Usage: $0 <prod_user@prod_host> <prod_db_url>}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
ADMIN_EMAIL="${ADMIN_EMAIL:-yugoja20@gmail.com}"
ADMIN_PASS="${ADMIN_PASS:-devpass}"
LOCAL_SQL="/tmp/player_form_all.sql"
PROD_SQL="/tmp/player_form_all.sql"

# Team IDs 1–48 (matches teams table in DB)
ALL_TEAM_IDS=($(seq 1 48))

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

# ── Step 2: Seed team by team ──────────────────────────────────────────────────
SEEDED=0
SKIPPED=0
FAILED=0

for TEAM_ID in "${ALL_TEAM_IDS[@]}"; do
  # Get team name for display
  TEAM_NAME=$(docker exec lazyfantasy-db psql -U lazyfantasy -d lazyfantasy_dev -t -A \
    -c "SELECT name FROM teams WHERE id=${TEAM_ID} AND sport='football';" 2>/dev/null || echo "team $TEAM_ID")

  echo ""
  echo "── Team ${TEAM_ID}/48: ${TEAM_NAME} ──"

  # Snapshot log line count before triggering so we only look at new lines after
  LOG_LINES_BEFORE=$(docker logs lazyfantasy-backend 2>&1 | wc -l)

  # Trigger seed for this single team
  RESPONSE=$(curl -sf -X POST "$BACKEND_URL/admin/wc/seed-player-form" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "{\"wc_league_id\": 1, \"season\": 2026, \"team_ids\": [${TEAM_ID}]}" 2>&1 || true)

  if [[ -z "$RESPONSE" ]]; then
    echo "  ✗ Request failed (backend unreachable?)"
    FAILED=$((FAILED + 1))
    continue
  fi

  # Wait for this team's seed to complete
  ATTEMPTS=0
  MAX_ATTEMPTS=30  # 5 minutes per team
  DONE=false
  until $DONE; do
    sleep 10
    ATTEMPTS=$((ATTEMPTS + 1))

    # Only look at log lines added after we triggered this team
    LAST_LOG=$(docker logs lazyfantasy-backend 2>&1 | tail -n "+$((LOG_LINES_BEFORE + 1))" | grep "seed-player-form complete" | tail -1)

    if [[ -n "$LAST_LOG" ]]; then
      echo "  ✓ $LAST_LOG"
      DONE=true

      if echo "$LAST_LOG" | grep -q "skipped=1"; then
        SKIPPED=$((SKIPPED + 1))
        echo "  (already seeded, skipped)"
      else
        SEEDED=$((SEEDED + 1))
      fi

      # Check if all covered
      if echo "$LAST_LOG" | grep -q "all_covered=True"; then
        echo ""
        echo "🎉 All 48 teams covered!"
        break 2
      fi
    fi

    if [[ $ATTEMPTS -ge $MAX_ATTEMPTS ]]; then
      echo "  ✗ Timed out waiting for team $TEAM_ID. Check docker logs lazyfantasy-backend"
      FAILED=$((FAILED + 1))
      DONE=true
    else
      echo "  ... waiting (${ATTEMPTS}/${MAX_ATTEMPTS})"
    fi
  done

  # Brief pause between teams so the background task finishes fully
  sleep 3
done

echo ""
echo "── Seed complete: seeded=${SEEDED} skipped=${SKIPPED} failed=${FAILED} ──"

# ── Step 3: Generate SQL dump (name-based, safe for prod) ─────────────────────
echo ""
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

# ── Step 4: Copy to prod ───────────────────────────────────────────────────────
echo "→ Copying SQL to $PROD_HOST..."
scp "$LOCAL_SQL" "${PROD_HOST}:${PROD_SQL}"
echo "  ✓ Copied"

# ── Step 5: Apply on prod ──────────────────────────────────────────────────────
echo "→ Applying on prod..."
ssh "$PROD_HOST" "psql '${PROD_DB_URL}' -f ${PROD_SQL} -v ON_ERROR_STOP=0 2>&1 | tail -5"
echo "  ✓ Done"

echo ""
echo "✅ All done. Player form data is live on prod."
echo "   Re-run anytime — all statements are idempotent upserts."
