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
ARTIFACTS_STORE_NAME=fileSearchStores/your-artifacts-store-id
SUPABASE_URL=https://awpeffqeuhatqkaryffh.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
DUMPLING_API_KEY=your-dumpling-key
LOG_LEVEL=INFO
```

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
