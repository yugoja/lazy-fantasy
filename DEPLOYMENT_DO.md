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
cat > .env << EOF
DATABASE_URL=postgresql://lazy_fantasy_db_admin:your_secure_password_here@localhost:5432/lazy_fantasy_league
SECRET_KEY=$(openssl rand -hex 32)
CORS_ORIGINS=http://YOUR_DROPLET_IP,https://yourdomain.com
FRONTEND_URL=http://YOUR_DROPLET_IP
EOF

# Initialize database
python -c "from app.database import engine; from app.models import Base; Base.metadata.create_all(bind=engine)"

# Seed data (optional)
python seed_wpl.py

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

**Frontend service** (`/etc/systemd/system/fantasy-frontend.service`):
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
   journalctl -u fantasy-backend -f
   journalctl -u fantasy-frontend -f
   ```

---

## Updating the App

When you push new code:

```bash
ssh root@YOUR_DROPLET_IP

su - lazy-fantasy
cd /home/fantasy/app
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
systemctl restart fantasy-backend fantasy-frontend
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| 502 Bad Gateway | Check if services are running: `systemctl status fantasy-backend` |
| Database connection error | Check PostgreSQL: `sudo -u postgres psql -c "\l"` |
| Frontend not loading | Check frontend logs: `journalctl -u fantasy-frontend -f` |
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
