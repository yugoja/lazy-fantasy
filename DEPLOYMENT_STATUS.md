# DigitalOcean Deployment Status

## ✅ Completed Steps

### Step 1: Create Droplet ✓
- Droplet created
- IP address obtained

### Step 2: Initial Server Setup ✓
- System updated
- PostgreSQL installed
- Python 3.12 installed
- Node.js 20 installed
- Nginx installed
- App user created (`lazy-fantasy`)

---

## 🚨 CRITICAL UPDATES NEEDED

Before continuing with the guide, these files need updates:

### 1. Fix Systemd Service Files (Step 5)

**Current issue:** Service files reference wrong username
- Guide says: `User=fantasy`
- Actual username: `lazy-fantasy`

**Fixed service files below** ⬇️

### 2. Add Admin Migration Step

Need to add `is_admin` column to production database

### 3. Update Frontend Environment Variable

Need to set correct API URL in production

---

## 📋 Your Next Steps (Step by Step)

### Step 3: Setup PostgreSQL ⏭️ **START HERE**

```bash
# SSH into your droplet
ssh root@YOUR_DROPLET_IP

# Create database and user
sudo -u postgres psql << EOF
CREATE USER lazy_fantasy_db_admin WITH PASSWORD 'YOUR_STRONG_PASSWORD_HERE';
CREATE DATABASE lazy_fantasy_league OWNER lazy_fantasy_db_admin;
GRANT ALL PRIVILEGES ON DATABASE lazy_fantasy_league TO lazy_fantasy_db_admin;
\q
EOF
```

**✏️ TODO:**
- [ ] Replace `YOUR_STRONG_PASSWORD_HERE` with actual strong password
- [ ] Save this password - you'll need it for the .env file

---

### Step 4: Deploy Application ⏭️ **NEXT**

#### A. Clone Repository

```bash
# Switch to app user
su - lazy-fantasy
cd /home/lazy-fantasy/app

# Clone your repo (you need to create GitHub repo first!)
git clone https://github.com/YOUR_USERNAME/lazy-fantasy.git .
```

**⚠️ BLOCKER:** Is your code on GitHub yet?
- [ ] Push code to GitHub
- [ ] Use the clone URL above

#### B. Setup Backend

```bash
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### C. Create .env File

**🔥 IMPORTANT: Use the CORRECT values**

```bash
cat > .env << 'EOF'
DATABASE_URL=postgresql://lazy_fantasy_db_admin:YOUR_DB_PASSWORD@localhost:5432/lazy_fantasy_league
SECRET_KEY=6RAPACEppOYSwInC91LgNk8P6HaJyOrqBlFsyXl_uJU
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
CORS_ORIGINS=http://YOUR_DROPLET_IP
FRONTEND_URL=http://YOUR_DROPLET_IP
EOF
```

**✏️ TODO:**
- [ ] Replace `YOUR_DB_PASSWORD` with PostgreSQL password from Step 3
- [ ] Replace `YOUR_DROPLET_IP` with actual IP (e.g., `167.99.123.45`)

#### D. Initialize Database

```bash
# Create tables
python -c "from app.database import engine; from app.models.base import Base; Base.metadata.create_all(bind=engine)"

# 🆕 Add is_admin column
python migrate_add_admin.py

# Seed initial data
python seed_wpl.py

# 🆕 Make yourself admin
python make_admin.py yugoja
```

#### E. Setup Frontend

```bash
cd ../frontend

# Create production environment
cat > .env.local << 'EOF'
NEXT_PUBLIC_API_URL=http://YOUR_DROPLET_IP
EOF

npm install
npm run build

exit  # Back to root
```

**✏️ TODO:**
- [ ] Replace `YOUR_DROPLET_IP` with actual IP

---

### Step 5: Create Systemd Services ⏭️

**🔥 CORRECTED SERVICE FILES (username fixed)**

#### Backend Service

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

#### Frontend Service

```bash
cat > /etc/systemd/system/lazy-fantasy-frontend.service << 'EOF'
[Unit]
Description=Lazy Fantasy Frontend
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

#### Start Services

```bash
systemctl daemon-reload
systemctl enable lazy-fantasy-backend lazy-fantasy-frontend
systemctl start lazy-fantasy-backend lazy-fantasy-frontend

# Check status
systemctl status lazy-fantasy-backend
systemctl status lazy-fantasy-frontend
```

**✅ Expected Output:**
- Both should show `active (running)` in green
- If not, check logs: `journalctl -u lazy-fantasy-backend -n 50`

---

### Step 6: Configure Nginx ⏭️

```bash
cat > /etc/nginx/sites-available/lazy-fantasy << 'EOF'
server {
    listen 80;
    server_name YOUR_DROPLET_IP;

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
    location ~ ^/(auth|matches|leagues|predictions|admin|health|docs|openapi.json)/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
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

**✏️ TODO:**
- [ ] Replace `YOUR_DROPLET_IP` with actual IP

---

### Step 7: Setup Firewall 🔒

```bash
# Enable firewall
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

# Check status
ufw status
```

---

## 🧪 Testing Your Deployment

After completing all steps:

### 1. Test Backend

```bash
curl http://YOUR_DROPLET_IP/health
# Expected: {"status":"healthy"}
```

### 2. Test Frontend

Open in browser:
```
http://YOUR_DROPLET_IP
```

Should see the Fantasy Cricket League homepage!

### 3. Test Admin Login

1. Go to `http://YOUR_DROPLET_IP/login`
2. Login as `yugoja`
3. Try creating a match (admin feature)
4. Should work! ✅

---

## 📊 Deployment Checklist

### Before Starting
- [x] Droplet created
- [x] Initial server setup complete
- [ ] Code pushed to GitHub
- [ ] Strong database password chosen

### Step 3: PostgreSQL
- [ ] Database created
- [ ] User created
- [ ] Password saved

### Step 4: Application
- [ ] Code cloned from GitHub
- [ ] Backend .env created
- [ ] Database initialized
- [ ] Admin user created
- [ ] Frontend .env.local created
- [ ] Frontend built

### Step 5: Services
- [ ] Backend service created
- [ ] Frontend service created
- [ ] Services started
- [ ] Services running (green status)

### Step 6: Nginx
- [ ] Nginx config created
- [ ] Config enabled
- [ ] Nginx reloaded

### Step 7: Security
- [ ] Firewall enabled
- [ ] Only SSH & HTTP/HTTPS open

### Testing
- [ ] Backend health check works
- [ ] Frontend loads in browser
- [ ] Can sign up
- [ ] Can login
- [ ] Admin can create matches
- [ ] Predictions work
- [ ] Leaderboards work

---

## 🚨 Common Issues & Solutions

### Issue: Service won't start

```bash
# Check logs
journalctl -u lazy-fantasy-backend -n 50

# Common fixes:
# 1. Wrong username in service file (should be lazy-fantasy)
# 2. Wrong path to app
# 3. Database connection error (check .env)
```

### Issue: Can't connect to database

```bash
# Test database connection
sudo -u postgres psql lazy_fantasy_league -c "SELECT 1;"

# Check if user exists
sudo -u postgres psql -c "\du"
```

### Issue: Frontend shows "Failed to fetch"

- Check CORS_ORIGINS in backend .env
- Check NEXT_PUBLIC_API_URL in frontend .env.local
- Verify both services are running

### Issue: 502 Bad Gateway

```bash
# Check if backend is running
systemctl status lazy-fantasy-backend

# Check what's listening on port 8000
netstat -tlnp | grep 8000
```

---

## 📝 Quick Reference

### Useful Commands

```bash
# Check service status
systemctl status lazy-fantasy-backend
systemctl status lazy-fantasy-frontend

# View logs
journalctl -u lazy-fantasy-backend -f
journalctl -u lazy-fantasy-frontend -f

# Restart services
systemctl restart lazy-fantasy-backend
systemctl restart lazy-fantasy-frontend

# Check Nginx
nginx -t
systemctl status nginx
```

---

## ✅ When Complete

After successful deployment:

1. **Test everything** using the checklist above
2. **Share with beta testers**: `http://YOUR_DROPLET_IP`
3. **Monitor logs** for first few hours
4. **Backup database** regularly:
   ```bash
   pg_dump -U lazy_fantasy_db_admin lazy_fantasy_league > backup.sql
   ```

---

## 🎯 Is It Ready?

**YES, the guide is complete** for beta deployment! Just follow the steps above in order.

**Estimated time:** 20-30 minutes for Steps 3-7

**Need help?** Stop at any step and ask!
