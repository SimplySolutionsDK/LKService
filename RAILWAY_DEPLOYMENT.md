# Railway Deployment Guide

Complete guide for deploying LKService to Railway with Danløn integration.

## Prerequisites

1. Railway account (sign up at https://railway.app)
2. GitHub repository connected to Railway
3. Danløn integration credentials (client ID and secret)

## Step 1: Create Railway Project

1. Go to https://railway.app/dashboard
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your LKService repository
5. Railway will auto-detect it's a Python project

## Step 2: Add PostgreSQL Database (Optional but Recommended)

Railway provides PostgreSQL as a service:

1. Click "+ New" in your project
2. Select "Database" → "PostgreSQL"
3. Railway will automatically create a `DATABASE_URL` environment variable

**Note:** The app works with SQLite by default, but PostgreSQL is better for production.

## Step 3: Configure Environment Variables

In Railway, go to your service → "Variables" tab and add:

### Required Variables

```bash
# Application
APP_BASE_URL=https://your-app.up.railway.app
NODE_ENV=production

# Danløn OAuth (Demo)
DANLON_ENVIRONMENT=demo
DANLON_CLIENT_ID=partner-showcase
DANLON_CLIENT_SECRET=ZwgcjNrJcspNCTFWDhtL4rgAyPTa4s82

# Or Danløn OAuth (Production)
# DANLON_ENVIRONMENT=prod
# DANLON_CLIENT_ID=simplysolutions
# DANLON_CLIENT_SECRET=oFqALlksfa3xK2CcQJXbXXaofXDH79Qd
```

### Optional Variables (if not using Railway's PostgreSQL)

```bash
# Use SQLite (default if DATABASE_URL not set)
# No configuration needed - will create lkservice.db file

# Or use your own PostgreSQL
# DATABASE_URL=postgresql+asyncpg://user:password@host:port/dbname
```

### Core API Variables (if you have them)

```bash
CORE_API_URL=https://your-api.com
API_AUTH_KEY=your_api_key
APIM_SUBSCRIPTION_KEY=your_subscription_key
```

## Step 4: Update APP_BASE_URL After First Deploy

Railway assigns you a URL after first deployment:

1. Deploy the app first
2. Note the Railway URL (e.g., `lkservice-production-xxxx.up.railway.app`)
3. Update `APP_BASE_URL` to: `https://lkservice-production-xxxx.up.railway.app`
4. Redeploy (Railway auto-deploys on variable change)

**Important:** The URL must match exactly for OAuth callbacks to work!

## Step 5: Build Configuration

Railway auto-detects Python projects. If needed, create `railway.toml`:

```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 100
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 10
```

## Step 6: Frontend Build (if needed)

If you want to serve the frontend from Railway:

Add to your build command (Railway detects automatically):

```bash
# Build frontend
cd frontend && npm install && npm run build
```

The FastAPI app already serves the built frontend from `/`.

## Database Configuration

### Using Railway's PostgreSQL

Railway automatically sets `DATABASE_URL`. The app will:
1. Detect it's PostgreSQL
2. Convert `postgres://` to `postgresql+asyncpg://`
3. Create tables automatically on startup

### Using SQLite (Default)

If no `DATABASE_URL` is set:
1. App creates `lkservice.db` in the project root
2. Works fine for development and small production use
3. Data persists across deploys (Railway provides persistent storage)

### Verifying Database

Check logs on Railway:
```
Initializing database...
Database initialized successfully
```

## Step 7: Test Deployment

1. Open your Railway URL: `https://your-app.up.railway.app`
2. You should see the LKService interface
3. Check health endpoint: `https://your-app.up.railway.app/health`
4. Should return: `{"status": "healthy", "service": "Time Registration CSV Parser"}`

## Step 8: Test Danløn Integration

### 8.1 Test Connection

1. Navigate to your app
2. Expand "Danløn Integration" section
3. Click "Connect to Danløn"
4. You should be redirected to Danløn login
5. Login with demo credentials
6. Select company
7. Should redirect back to your app showing "Connected"

### 8.2 Test Sync

1. Upload and process a CSV (or fetch from API)
2. Once you have preview data
3. In Danløn Integration section, click "Sync to Danløn"
4. Should show success with created payparts count

## Troubleshooting

### Issue: OAuth redirect fails

**Problem:** "Redirect URI mismatch" error

**Solution:**
1. Check `APP_BASE_URL` matches your Railway URL exactly
2. Include `https://` protocol
3. No trailing slash
4. Redeploy after changing

---

### Issue: Database connection fails

**Problem:** "No module named 'asyncpg'" or similar

**Solution:**
1. Ensure `asyncpg` is in `requirements.txt`
2. Railway should auto-install it
3. Check build logs for installation errors

---

### Issue: Environment variables not working

**Problem:** Variables not being read

**Solution:**
1. Variables in Railway are automatically available
2. No `.env` file needed on Railway
3. Restart deployment after adding variables
4. Check logs for "DANLON_CLIENT_SECRET environment variable not set"

---

### Issue: Frontend not loading

**Problem:** API works but frontend shows error

**Solution:**
1. Check if frontend was built: `frontend/dist` should exist
2. Rebuild frontend: `cd frontend && npm run build`
3. Railway should serve frontend from `/`
4. API docs available at `/docs`

---

### Issue: Tokens not persisting

**Problem:** Connection lost after restart

**Solution with PostgreSQL:**
1. Use Railway's PostgreSQL database
2. Set `DATABASE_URL` (should be automatic)
3. Tokens stored in database, persist across restarts

**Solution with SQLite:**
1. Ensure Railway has persistent storage enabled (default)
2. Check `lkservice.db` is in project root
3. Database file persists across deploys

---

### Issue: CORS errors

**Problem:** Frontend can't connect to API

**Solution:**
1. Not an issue when frontend served by FastAPI
2. If using separate frontend deployment, add CORS middleware
3. Check Railway logs for CORS errors

## Monitoring and Logs

### View Logs

In Railway:
1. Go to your service
2. Click "Logs" tab
3. See real-time logs

Look for:
- `Initializing database...` on startup
- `Database initialized successfully`
- OAuth flow logs (connect, token refresh, etc.)
- Sync operation logs

### Check Database

For PostgreSQL on Railway:

1. Go to PostgreSQL service
2. Click "Connect"
3. Use provided credentials to connect with a client
4. Query `danlon_tokens` table to see stored tokens

```sql
SELECT user_id, company_id, company_name, expires_at, created_at 
FROM danlon_tokens;
```

## Security Checklist

- [ ] `DANLON_CLIENT_SECRET` is set in Railway (not committed to git)
- [ ] `APP_BASE_URL` points to your Railway HTTPS URL
- [ ] Database credentials (if custom) are in Railway Variables
- [ ] `.env` file is in `.gitignore`
- [ ] No secrets committed to repository
- [ ] HTTPS is enabled (Railway does this automatically)

## Scaling

Railway auto-scales based on your plan:

**Starter Plan:**
- Good for development and testing
- Handles moderate traffic
- SQLite or PostgreSQL

**Pro Plan:**
- Better for production
- PostgreSQL recommended
- Auto-scaling
- Better uptime

## Updating Production

Railway auto-deploys when you push to main branch:

1. Make changes locally
2. Test thoroughly
3. Commit and push to GitHub
4. Railway automatically deploys
5. Check logs for successful deployment

## Environment-Specific Configuration

### Demo Environment (Testing)

```bash
DANLON_ENVIRONMENT=demo
DANLON_CLIENT_ID=partner-showcase
DANLON_CLIENT_SECRET=ZwgcjNrJcspNCTFWDhtL4rgAyPTa4s82
APP_BASE_URL=https://your-demo-app.up.railway.app
```

### Production Environment (Live)

```bash
DANLON_ENVIRONMENT=prod
DANLON_CLIENT_ID=simplysolutions
DANLON_CLIENT_SECRET=oFqALlksfa3xK2CcQJXbXXaofXDH79Qd
APP_BASE_URL=https://your-prod-app.up.railway.app
```

**Tip:** Use Railway's "Environments" feature to have separate demo and prod deployments.

## Database Migration (if needed)

If you start with SQLite and want to migrate to PostgreSQL:

1. Add PostgreSQL service in Railway
2. `DATABASE_URL` is automatically set
3. Redeploy - new tables created automatically
4. Old SQLite data: export and import manually if needed

## Backup Strategy

### With PostgreSQL:

Use Railway's built-in backups or:

```bash
# Export tokens
pg_dump -U user -h host -d dbname -t danlon_tokens > backup.sql

# Import
psql -U user -h host -d dbname < backup.sql
```

### With SQLite:

- Download `lkservice.db` file from Railway
- Store in secure location
- Can restore by uploading back to Railway

## Next Steps After Deployment

1. ✅ Deploy to Railway
2. ✅ Configure environment variables
3. ✅ Test OAuth connection flow
4. ✅ Test data sync
5. ⬜ Set up monitoring/alerts
6. ⬜ Configure custom domain (if needed)
7. ⬜ Set up production Danløn credentials
8. ⬜ Train users on the system

## Support

For Railway-specific issues:
- Railway Docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway

For LKService/Danløn issues:
- Check logs in Railway
- Review `DANLON_INTEGRATION.md`
- Check `TROUBLESHOOTING.md` (if exists)

## Success Checklist

Deployment is successful when:

- [ ] App loads at Railway URL
- [ ] Health check passes (`/health`)
- [ ] Can upload CSV and see preview
- [ ] Can connect to Danløn OAuth
- [ ] Connection persists after restart
- [ ] Can sync data to Danløn
- [ ] No errors in Railway logs
- [ ] Database is working (tokens stored)

## Quick Reference

```bash
# Railway URL structure
https://[project-name]-[environment].up.railway.app

# Important endpoints
/                    # Frontend
/health              # Health check
/docs                # API documentation
/danlon/connect      # Start OAuth flow
/danlon/status       # Check connection

# Database location (SQLite)
./lkservice.db

# Logs
railway logs

# Redeploy
git push origin main
```

Your LKService app is now deployed to Railway with full Danløn integration! 🚀
