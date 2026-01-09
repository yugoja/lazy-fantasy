# Deployment Guide - Fantasy Cricket League on Render

This guide walks you through deploying the Fantasy Cricket League app to [Render](https://render.com).

## Prerequisites

- A [Render account](https://dashboard.render.com/register) (free)
- Your code pushed to a GitHub repository

---

## Quick Deploy (Recommended)

Use the included `render.yaml` Blueprint for one-click deployment:

1. Push your code to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com)
3. Click **New** → **Blueprint**
4. Connect your GitHub repo
5. Render will auto-detect `render.yaml` and create:
   - PostgreSQL database
   - Backend API service
   - Frontend static site

6. After deployment, set these environment variables:

   **Backend (fantasy-cricket-api):**
   | Variable | Value |
   |----------|-------|
   | `CORS_ORIGINS` | `https://fantasy-cricket-frontend.onrender.com` |
   | `FRONTEND_URL` | `https://fantasy-cricket-frontend.onrender.com` |

   **Frontend (fantasy-cricket-frontend):**
   | Variable | Value |
   |----------|-------|
   | `NEXT_PUBLIC_API_URL` | `https://fantasy-cricket-api.onrender.com` |

   > Replace with your actual Render URLs from the dashboard.

---

## Manual Deploy

### Step 1: Create PostgreSQL Database

1. Dashboard → **New** → **PostgreSQL**
2. Name: `fantasy-cricket-db`
3. Region: Oregon (or closest)
4. Plan: **Free**
5. Click **Create Database**
6. Copy the **Internal Database URL** for later

### Step 2: Deploy Backend

1. Dashboard → **New** → **Web Service**
2. Connect your GitHub repo
3. Configure:
   | Setting | Value |
   |---------|-------|
   | Name | `fantasy-cricket-api` |
   | Root Directory | `backend` |
   | Runtime | Python |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
   | Plan | Free |

4. Add Environment Variables:
   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | *(paste Internal Database URL from Step 1)* |
   | `SECRET_KEY` | *(generate a secure random string, 32+ chars)* |
   | `CORS_ORIGINS` | *(your frontend URL, set after Step 3)* |
   | `FRONTEND_URL` | *(your frontend URL, set after Step 3)* |

5. Click **Create Web Service**

### Step 3: Deploy Frontend

1. Dashboard → **New** → **Web Service**
2. Connect your GitHub repo
3. Configure:
   | Setting | Value |
   |---------|-------|
   | Name | `fantasy-cricket-frontend` |
   | Root Directory | `frontend` |
   | Runtime | Node |
   | Build Command | `npm install && npm run build` |
   | Start Command | `npm start` |
   | Plan | Free |

4. Add Environment Variable:
   | Key | Value |
   |-----|-------|
   | `NEXT_PUBLIC_API_URL` | `https://fantasy-cricket-api.onrender.com` |

5. Click **Create Web Service**

### Step 4: Update Backend CORS

Go back to your backend service and update:
- `CORS_ORIGINS` = your frontend URL (e.g., `https://fantasy-cricket-frontend.onrender.com`)
- `FRONTEND_URL` = same as above

---

## Seed Database (Optional)

After deployment, run the seed script via Render Shell:

1. Go to your backend service
2. Click **Shell** tab
3. Run:
   ```bash
   python seed_wpl.py
   ```

---

## Verify Deployment

1. Visit your frontend URL: `https://fantasy-cricket-frontend.onrender.com`
2. Try signing up a new account
3. Make a prediction

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| CORS errors | Check `CORS_ORIGINS` matches your frontend URL exactly |
| Database connection errors | Verify `DATABASE_URL` is the Internal URL, not External |
| 502 Bad Gateway | Check Render logs for startup errors |
| Slow cold starts | Free tier services sleep after 15 min inactivity |

---

## Free Tier Limits

| Resource | Limit |
|----------|-------|
| Web Services | 750 hours/month (shared across services) |
| PostgreSQL | 1 GB storage, 90 days then auto-delete |
| Bandwidth | 100 GB/month |

> **Tip:** For hobby projects, this is plenty! For production, consider paid tiers.
