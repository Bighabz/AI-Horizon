# Railway Deployment Guide

## Prerequisites
- Railway account: https://railway.app
- GitHub repository with this code

## Quick Deploy

### 1. Create Railway Project
1. Go to https://railway.app/new
2. Click "Deploy from GitHub repo"
3. Select your repository
4. Choose the `ai-horizon-python/ai-horizon-python` directory

### 2. Add Environment Variables
In Railway dashboard → Variables, add:

```
GEMINI_API_KEY=your-gemini-api-key
GEMINI_API_KEY_2=your-second-key
GEMINI_API_KEY_3=your-third-key
DCWF_STORE_NAME=fileSearchStores/your-store-id
EVIDENCE_STORE_NAME=fileSearchStores/your-evidence-store-id
RESOURCES_STORE_NAME=fileSearchStores/your-resources-store-id
ADMIN_API_KEY=your-admin-api-key
DUMPLING_API_KEY=your-dumpling-key
LOG_LEVEL=INFO
```

Add a Railway PostgreSQL plugin to the project; Railway injects `DATABASE_URL`
automatically (use a reference variable if the database lives in another service).

> Note: legacy Supabase variables (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`) are no
> longer used - the backend migrated to Railway PostgreSQL (see `src/api/db.py`).

### 3. Deploy
Railway will automatically:
- Detect Python
- Install dependencies from `requirements.txt`
- Run the start command from `railway.toml`

### 4. Get Your URL
After deploy, Railway provides a URL like:
`https://your-app.up.railway.app`

### 5. Update Frontend
Update `ai-horizon-frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=https://your-app.up.railway.app
```

## Manual Deploy via CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to project
cd ai-horizon-python/ai-horizon-python
railway link

# Deploy
railway up
```

## Monitoring
- View logs: Railway Dashboard → Deployments → View Logs
- Health check: `https://your-app.up.railway.app/api/stats`

## Costs
- Free tier: 500 hours/month, 512MB RAM
- Hobby: $5/month, always on, 8GB RAM
