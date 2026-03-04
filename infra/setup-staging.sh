#!/usr/bin/env bash
#
# One-time staging environment setup — run on the droplet as root.
#
# Usage:  ssh root@YOUR_DROPLET_IP 'bash -s' < infra/setup-staging.sh
#
set -euo pipefail

STAGING_DIR="/home/lazy-fantasy/staging"
REPO_URL="https://github.com/yugoja/lazy-fantasy.git"
APP_USER="lazy-fantasy"
DROPLET_IP="139.59.3.190"

echo "==> Setting up staging environment"

# ─── 1. Clone repo into staging directory ────────────────────────────────────
if [ -d "$STAGING_DIR/.git" ]; then
    echo "   Staging directory already exists, pulling latest..."
    sudo -u "$APP_USER" bash -c "cd $STAGING_DIR && git pull"
else
    echo "   Cloning repo into $STAGING_DIR..."
    mkdir -p "$STAGING_DIR"
    chown "$APP_USER:$APP_USER" "$STAGING_DIR"
    sudo -u "$APP_USER" git clone "$REPO_URL" "$STAGING_DIR"
fi

# ─── 2. Create staging PostgreSQL database ───────────────────────────────────
echo "── Creating staging database ──"
if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw lazy_fantasy_staging; then
    echo "   Database lazy_fantasy_staging already exists, skipping."
else
    sudo -u postgres psql << 'SQL'
CREATE DATABASE lazy_fantasy_staging OWNER lazy_fantasy_db_admin;
GRANT ALL PRIVILEGES ON DATABASE lazy_fantasy_staging TO lazy_fantasy_db_admin;
SQL
    echo "   ✓ Created lazy_fantasy_staging database"
fi

# ─── 3. Backend .env for staging ─────────────────────────────────────────────
echo "── Creating staging backend .env ──"
# Read the DB password from the prod .env to reuse the same DB user
PROD_DB_URL=$(grep '^DATABASE_URL=' /home/lazy-fantasy/app/backend/.env | cut -d= -f2-)
DB_PASSWORD=$(echo "$PROD_DB_URL" | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')

cat > "$STAGING_DIR/backend/.env" << ENVEOF
DATABASE_URL=postgresql://lazy_fantasy_db_admin:${DB_PASSWORD}@localhost:5432/lazy_fantasy_staging
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
CORS_ORIGINS=http://${DROPLET_IP}:8080
FRONTEND_URL=http://${DROPLET_IP}:8080
SENTRY_DSN=
SENTRY_ENVIRONMENT=staging
ENVEOF
chown "$APP_USER:$APP_USER" "$STAGING_DIR/backend/.env"
echo "   ✓ Created $STAGING_DIR/backend/.env"

# ─── 4. Frontend .env.local for staging ──────────────────────────────────────
echo "── Creating staging frontend .env.local ──"
cat > "$STAGING_DIR/frontend/.env.local" << ENVEOF
NEXT_PUBLIC_API_URL=http://${DROPLET_IP}:8080
ENVEOF
chown "$APP_USER:$APP_USER" "$STAGING_DIR/frontend/.env.local"
echo "   ✓ Created $STAGING_DIR/frontend/.env.local"

# ─── 5. Setup backend venv + deps ────────────────────────────────────────────
echo "── Setting up staging backend ──"
sudo -u "$APP_USER" bash -c "
    cd $STAGING_DIR/backend
    python3.12 -m venv venv
    source venv/bin/activate
    pip install -q -r requirements.txt
    python -c 'from app.database import engine; from app.models import Base; Base.metadata.create_all(bind=engine)'
"
echo "   ✓ Backend venv + DB tables ready"

# ─── 6. Build staging frontend ───────────────────────────────────────────────
echo "── Building staging frontend ──"
sudo -u "$APP_USER" bash -c "cd $STAGING_DIR/frontend && npm install && npm run build"
echo "   ✓ Frontend built"

# ─── 7. Create systemd services ──────────────────────────────────────────────
echo "── Creating systemd services ──"

cat > /etc/systemd/system/lazy-fantasy-staging-backend.service << 'EOF'
[Unit]
Description=Lazy Fantasy Staging Backend
After=network.target postgresql.service

[Service]
User=lazy-fantasy
Group=lazy-fantasy
WorkingDirectory=/home/lazy-fantasy/staging/backend
Environment="PATH=/home/lazy-fantasy/staging/backend/venv/bin"
ExecStart=/home/lazy-fantasy/staging/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/lazy-fantasy-staging-frontend.service << 'EOF'
[Unit]
Description=Lazy Fantasy Staging Frontend
After=network.target

[Service]
User=lazy-fantasy
Group=lazy-fantasy
WorkingDirectory=/home/lazy-fantasy/staging/frontend
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=3
Environment="NODE_ENV=production"
Environment="PORT=3001"

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable lazy-fantasy-staging-backend lazy-fantasy-staging-frontend
systemctl start lazy-fantasy-staging-backend lazy-fantasy-staging-frontend

echo "   ✓ Staging services created and started"

# ─── 8. Install nginx config ─────────────────────────────────────────────────
echo "── Updating nginx config ──"
# Copy the nginx config from the repo (or use the one already on disk)
if [ -f "$STAGING_DIR/infra/nginx.conf" ]; then
    cp "$STAGING_DIR/infra/nginx.conf" /etc/nginx/sites-available/lazy-fantasy
    ln -sf /etc/nginx/sites-available/lazy-fantasy /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    nginx -t && systemctl reload nginx
    echo "   ✓ Nginx config updated"
else
    echo "   ⚠ infra/nginx.conf not found in repo — update nginx manually"
fi

# ─── 9. Open UFW port for staging ────────────────────────────────────────────
echo "── Opening UFW port 8080 ──"
ufw allow 8080/tcp comment "Lazy Fantasy Staging" 2>/dev/null || true
echo "   ✓ UFW port 8080 open"

# ─── 10. Verify ──────────────────────────────────────────────────────────────
echo ""
echo "── Verifying staging services ──"
sleep 3
systemctl is-active lazy-fantasy-staging-backend && echo "   ✓ Staging backend running on :8001" || echo "   ✗ Staging backend not running"
systemctl is-active lazy-fantasy-staging-frontend && echo "   ✓ Staging frontend running on :3001" || echo "   ✗ Staging frontend not running"

echo ""
echo "==> Staging setup complete!"
echo "    Access staging at: http://${DROPLET_IP}:8080"
echo "    Staging DB: lazy_fantasy_staging"
echo "    Deploy with: ./deploy.sh staging"
