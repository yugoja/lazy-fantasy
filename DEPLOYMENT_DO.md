# DigitalOcean Droplet Deployment Guide

Deploy Fantasy Cricket League on a $6/month DigitalOcean Droplet with Nginx, PostgreSQL, and always-on performance.

## Prerequisites

- [DigitalOcean account](https://www.digitalocean.com/) 
- A domain (optional, can use Droplet IP)
- SSH key on your local machine

---

## Step 1: Create Droplet

1. Go to [DigitalOcean Dashboard](https://cloud.digitalocean.com/) → **Create** → **Droplets**
2. Configure:
   | Setting | Value |
   |---------|-------|
   | Region | Choose closest to your users |
   | Image | **Ubuntu 24.04 LTS** |
   | Size | **Basic → Regular → $6/mo** (1GB RAM, 1 vCPU) |
   | Authentication | **SSH Key** (recommended) |
   | Hostname | `fantasy-cricket` |

3. Click **Create Droplet**
4. Note the **IP address** (e.g., `167.99.xxx.xxx`)

---

## Step 2: Initial Server Setup

SSH into your server:
```bash
ssh root@YOUR_DROPLET_IP
```

Run the setup script (copy-paste this entire block):
```bash
# Update system
apt update && apt upgrade -y

# Install required packages
apt install -y python3.12 python3.12-venv python3-pip postgresql postgresql-contrib nginx certbot python3-certbot-nginx git curl

# Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# Create app user
useradd -m -s /bin/bash lazy-fantasy
mkdir -p /home/lazy-fantasy/app
chown lazy-fantasy:lazy-fantasy /home/lazy-fantasy/app
```

---

## Step 3: Setup PostgreSQL

```bash
# Switch to postgres user and create database
sudo -u postgres psql << EOF
CREATE USER lazy_fantasy_db_admin WITH PASSWORD 'your_secure_password_here';
CREATE DATABASE lazy_fantasy_league OWNER lazy_fantasy_db_admin;
GRANT ALL PRIVILEGES ON DATABASE lazy_fantasy_league TO lazy_fantasy_db_admin;
EOF
```

> ⚠️ **Change the password above!** Use a strong password.

---

## Step 4: Deploy Application

```bash
# Switch to fantasy user
su - lazy-fantasy
cd /home/lazy-fantasy/app

# Clone your repo
git clone https://github.com/yugoja/lazy-fantasy.git .

# Setup Backend
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env file
cat > .env << 'ENVEOF'
DATABASE_URL=postgresql://lazy_fantasy_db_admin:your_secure_password_here@localhost:5432/lazy_fantasy_league
SECRET_KEY=GENERATE_WITH_openssl_rand_-hex_32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
CORS_ORIGINS=http://YOUR_DROPLET_IP
FRONTEND_URL=http://YOUR_DROPLET_IP
SENTRY_DSN=
ENVEOF

# Initialize database
python -c "from app.database import engine; from app.models import Base; Base.metadata.create_all(bind=engine)"

# Seed data (optional)
python seed_t20wc.py

# Setup Frontend
cd ../frontend
npm install
npm run build

exit  # Back to root
```

---

## Step 5: Create Systemd Services

**Backend service** (`/etc/systemd/system/lazy-fantasy-backend.service`):
```bash
cat > /etc/systemd/system/lazy-fantasy-backend.service << 'EOF'
[Unit]
Description=Lazy Fantasy Backend
After=network.target postgresql.service

[Service]
User=lazy-fantasy
Group=lazy-fantasy
WorkingDirectory=/home/lazy-fantasy/app/backend
Environment="PATH=/home/lazy-fantasy/app/backend/venv/bin"
ExecStart=/home/lazy-fantasy/app/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
```

**Frontend service** (`/etc/systemd/system/lazy-fantasy-frontend.service`):
```bash
cat > /etc/systemd/system/lazy-fantasy-frontend.service << 'EOF'
[Unit]
Description=Fantasy Cricket Frontend
After=network.target

[Service]
User=lazy-fantasy
Group=lazy-fantasy
WorkingDirectory=/home/lazy-fantasy/app/frontend
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=3
Environment="NODE_ENV=production"
Environment="PORT=3000"

[Install]
WantedBy=multi-user.target
EOF
```

Enable and start services:
```bash
systemctl daemon-reload
systemctl enable lazy-fantasy-backend lazy-fantasy-frontend
systemctl start lazy-fantasy-backend lazy-fantasy-frontend

# Check status
systemctl status lazy-fantasy-backend
systemctl status lazy-fantasy-frontend
```

---

## Step 6: Configure Nginx

```bash
cat > /etc/nginx/sites-available/lazy-fantasy << 'EOF'
server {
    listen 80;
    server_name 139.59.3.190;  # Or your domain

    # Frontend
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api/ {
        rewrite ^/api/(.*) /$1 break;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Direct backend routes (auth, matches, etc.)
    location ~ ^/(auth|matches|leagues|predictions|admin|health)/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location = /health {
        proxy_pass http://127.0.0.1:8000;
    }
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/lazy-fantasy /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test and reload
nginx -t && systemctl reload nginx
```

---

## Step 7: Update Frontend Environment

The frontend needs to know the API is now on the same domain:

```bash
su - lazy-fantasy
cd /home/lazy-fantasy/app/frontend

# Create production env
echo "NEXT_PUBLIC_API_URL=http://139.59.3.190" > .env.local

# Rebuild
npm run build
exit

# Restart frontend
systemctl restart lazy-fantasy-frontend
```

---

## Step 8: (Optional) Add SSL with Let's Encrypt

If you have a domain pointing to your Droplet:

```bash
certbot --nginx -d yourdomain.com
```

Certbot will automatically configure HTTPS and set up auto-renewal.

---

## Verify Deployment

1. Visit `http://YOUR_DROPLET_IP` - should see the app
2. Check health: `curl http://YOUR_DROPLET_IP/health`
3. Check logs if issues:
   ```bash
   journalctl -u lazy-fantasy-backend -f
   journalctl -u lazy-fantasy-frontend -f
   ```

---

## Updating the App

When you push new code:

```bash
ssh root@YOUR_DROPLET_IP

su - lazy-fantasy
cd /home/lazy-fantasy/app
git pull

# Backend update
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Frontend update
cd ../frontend
npm install
npm run build

exit

# Restart services
systemctl restart lazy-fantasy-backend lazy-fantasy-frontend
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| 502 Bad Gateway | Check if services are running: `systemctl status lazy-fantasy-backend` |
| Database connection error | Check PostgreSQL: `sudo -u postgres psql -c "\l"` |
| Frontend not loading | Check frontend logs: `journalctl -u lazy-fantasy-frontend -f` |
| Can't connect to server | Check firewall: `ufw status` |

---

## Security (Recommended)

```bash
# Enable firewall
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable

# Create non-root user for SSH (optional but recommended)
adduser deploy
usermod -aG sudo deploy
```

---

## Cost Summary

| Resource | Cost |
|----------|------|
| Droplet (1GB) | $6/month |
| Total | **$6/month** |

Always-on, no cold starts, full control! 🚀

---

## Staging Environment

A staging environment runs on the same droplet at zero extra cost — separate database, separate ports, accessed via `:8080`.

| Component | Production | Staging |
|-----------|-----------|---------|
| Backend port | 8000 | 8001 |
| Frontend port | 3000 | 3001 |
| Nginx port | 80 | 8080 |
| Working dir | `/home/lazy-fantasy/app` | `/home/lazy-fantasy/staging` |
| Database | `lazy_fantasy_league` | `lazy_fantasy_staging` |
| Access URL | `https://lazyfantasy.app` | `https://staging.lazyfantasy.app` |
| Sentry env | `production` | `staging` |

### First-time setup

Run the bootstrap script from your local machine:

```bash
ssh root@YOUR_DROPLET_IP 'bash -s' < infra/setup-staging.sh
```

This creates the staging directory, database, `.env` files, systemd services, updates nginx, and opens UFW port 8080.

### Deploy workflow (GitHub Actions)

Deployments are triggered automatically via GitHub Actions (`.github/workflows/deploy.yml`):

| Branch | Environment | URL |
|--------|-------------|-----|
| `staging` | Staging | `http://YOUR_DROPLET_IP:8080` |
| `main` | Production | `http://YOUR_DROPLET_IP` |

```bash
# Deploy to staging
git checkout staging
git merge main       # or cherry-pick specific commits
git push origin staging
# GitHub Actions deploys → verify at http://YOUR_DROPLET_IP:8080

# Promote to production
git checkout main
git merge staging
git push origin main
# GitHub Actions deploys → verify at http://YOUR_DROPLET_IP
```

**Required GitHub secrets** (Settings → Secrets → Actions):
- `DROPLET_IP` — droplet IP address
- `SSH_PRIVATE_KEY` — SSH private key for root access

**Manual fallback** (if CI is down):
```bash
./deploy.sh staging   # or: ./deploy.sh prod
```

### Nginx config

The nginx config lives at `infra/nginx.conf` and covers both production and staging server blocks. To update nginx after editing:

```bash
scp infra/nginx.conf root@YOUR_DROPLET_IP:/etc/nginx/sites-available/lazy-fantasy
ssh root@YOUR_DROPLET_IP 'nginx -t && systemctl reload nginx'
```

### Useful commands

```bash
# Check staging services
ssh root@YOUR_DROPLET_IP 'systemctl status lazy-fantasy-staging-backend lazy-fantasy-staging-frontend'

# Staging logs
ssh root@YOUR_DROPLET_IP 'journalctl -u lazy-fantasy-staging-backend -f'

# Health check
curl http://YOUR_DROPLET_IP:8080/health

# Connect to staging database
ssh root@YOUR_DROPLET_IP 'sudo -u postgres psql lazy_fantasy_staging'
```
