#!/usr/bin/env bash
#
# Manual deploy fallback — prefer pushing to main/staging branch
# which triggers GitHub Actions (.github/workflows/deploy.yml).
#
# Usage: ./deploy.sh staging   # deploy to staging (port 8080)
#        ./deploy.sh prod      # deploy to production (port 80)
#
set -euo pipefail

# ─── Configuration ───────────────────────────────────────────────────────────
DROPLET_HOST="${DROPLET_HOST:-root@139.59.3.190}"
APP_USER="lazy-fantasy"

# Environment-specific settings
declare -A DIR=( [prod]="/home/lazy-fantasy/app" [staging]="/home/lazy-fantasy/staging" )
declare -A BACKEND_SVC=( [prod]="lazy-fantasy-backend" [staging]="lazy-fantasy-staging-backend" )
declare -A FRONTEND_SVC=( [prod]="lazy-fantasy-frontend" [staging]="lazy-fantasy-staging-frontend" )
declare -A MIGRATIONS_DIR=( [prod]="/home/lazy-fantasy/app/backend/migrations" [staging]="/home/lazy-fantasy/staging/backend/migrations" )

# ─── Argument parsing ────────────────────────────────────────────────────────
ENV="${1:-}"
if [[ "$ENV" != "prod" && "$ENV" != "staging" ]]; then
    echo "Usage: ./deploy.sh <prod|staging>"
    echo ""
    echo "  ./deploy.sh staging   # deploy to staging (port 8080)"
    echo "  ./deploy.sh prod      # deploy to production (port 80)"
    exit 1
fi

echo "==> Deploying to $ENV on $DROPLET_HOST"

# ─── Deploy via SSH ──────────────────────────────────────────────────────────
ssh -o StrictHostKeyChecking=accept-new "$DROPLET_HOST" bash -s "$ENV" "${DIR[$ENV]}" "${BACKEND_SVC[$ENV]}" "${FRONTEND_SVC[$ENV]}" "${MIGRATIONS_DIR[$ENV]}" "$APP_USER" << 'REMOTE_SCRIPT'
set -euo pipefail

ENV="$1"
APP_DIR="$2"
BACKEND_SVC="$3"
FRONTEND_SVC="$4"
MIGRATIONS_DIR="$5"
APP_USER="$6"

echo "── Pulling latest code ──"
sudo -u "$APP_USER" bash -c "cd $APP_DIR && git pull"

echo "── Installing backend dependencies ──"
sudo -u "$APP_USER" bash -c "cd $APP_DIR/backend && source venv/bin/activate && pip install -q -r requirements.txt"

echo "── Running pending migrations ──"
if [ -d "$MIGRATIONS_DIR" ]; then
    for sql_file in "$MIGRATIONS_DIR"/*.sql; do
        [ -f "$sql_file" ] || continue
        echo "   Running: $(basename "$sql_file")"
        # Read DATABASE_URL from backend .env to get the DB name
        DB_URL=$(grep '^DATABASE_URL=' "$APP_DIR/backend/.env" | cut -d= -f2-)
        DB_NAME=$(echo "$DB_URL" | sed 's|.*/||')
        sudo -u postgres psql -d "$DB_NAME" -f "$sql_file" 2>&1 | head -5
    done
else
    echo "   No migrations directory found, skipping."
fi

echo "── Installing frontend dependencies + building ──"
sudo -u "$APP_USER" bash -c '
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
    cd '"$APP_DIR/frontend"' && npm install --production=false && npm run build
'

echo "── Restarting services ──"
systemctl restart "$BACKEND_SVC" "$FRONTEND_SVC"

echo "── Checking service status ──"
sleep 2
systemctl is-active "$BACKEND_SVC" && echo "   ✓ $BACKEND_SVC is running" || echo "   ✗ $BACKEND_SVC failed"
systemctl is-active "$FRONTEND_SVC" && echo "   ✓ $FRONTEND_SVC is running" || echo "   ✗ $FRONTEND_SVC failed"

echo "── Recent backend logs ──"
journalctl -u "$BACKEND_SVC" --no-pager -n 10

echo ""
echo "==> $ENV deploy complete!"
REMOTE_SCRIPT

echo "==> Done. Deployed $ENV successfully."
