# AI Horizon Deployment Guide

## Quick Start (Local Development)

```bash
# 1. Clone and setup
cd ai-horizon-python
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 3. Initialize Gemini File Search stores
python scripts/setup_file_stores.py

# 4. Import DCWF data (optional but recommended)
python scripts/import_dcwf.py --file data/dcwf/dcwf_tasks.json

# 5. Start the API server
uvicorn src.api.main:app --reload --port 8000

# 6. Open the web interface
# Open src/static/index.html in your browser
# Or serve it: python -m http.server 3000 --directory src/static
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/api/chat` | POST | RAG-powered chat |
| `/api/search` | POST | Search tasks/artifacts |
| `/api/submit` | POST | Submit new evidence |
| `/api/evidence/{task_id}` | GET | Get evidence for task |
| `/api/roles` | GET | List all job roles |
| `/api/stats` | GET | Knowledge base statistics |

## Deployment Options

### Option 1: Railway / Render (Easiest)

```bash
# railway.json or render.yaml
{
  "build": {
    "builder": "DOCKERFILE"
  },
  "deploy": {
    "startCommand": "uvicorn src.api.main:app --host 0.0.0.0 --port $PORT"
  }
}
```

### Option 2: Google Cloud Run

```bash
# Build and deploy
gcloud builds submit --tag gcr.io/YOUR_PROJECT/ai-horizon
gcloud run deploy ai-horizon --image gcr.io/YOUR_PROJECT/ai-horizon --platform managed
```

### Option 3: DigitalOcean App Platform

1. Connect your GitHub repo
2. Set environment variables (GEMINI_API_KEY, etc.)
3. Deploy

### Option 4: Self-hosted VPS

```bash
# On your VPS (Ubuntu)
sudo apt update && sudo apt install python3.11 python3.11-venv nginx certbot

# Clone and setup
git clone https://github.com/YOUR_REPO/ai-horizon-python
cd ai-horizon-python
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Add your keys

# Run with systemd
sudo nano /etc/systemd/system/ai-horizon.service
```

```ini
[Unit]
Description=AI Horizon API
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/ai-horizon-python
Environment="PATH=/var/www/ai-horizon-python/venv/bin"
EnvironmentFile=/var/www/ai-horizon-python/.env
ExecStart=/var/www/ai-horizon-python/venv/bin/uvicorn src.api.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-horizon
sudo systemctl start ai-horizon

# Nginx reverse proxy
sudo nano /etc/nginx/sites-available/ai-horizon
```

```nginx
server {
    listen 80;
    server_name api.theaihorizon.org;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/ai-horizon /etc/nginx/sites-enabled/
sudo certbot --nginx -d api.theaihorizon.org
sudo systemctl restart nginx
```

## Integrating with theaihorizon.org

### Option A: Embed as iframe

```html
<!-- On theaihorizon.org/forecast page -->
<iframe 
    src="https://api.theaihorizon.org/static/index.html" 
    width="100%" 
    height="800px" 
    frameborder="0">
</iframe>
```

### Option B: API calls from existing site

```javascript
// On theaihorizon.org
const API = 'https://api.theaihorizon.org';

// Search
fetch(`${API}/api/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: 'threat analyst' })
})
.then(res => res.json())
.then(data => console.log(data.results));

// Chat
fetch(`${API}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
        message: 'What jobs will AI replace?',
        session_id: 'user-123'
    })
})
.then(res => res.json())
.then(data => console.log(data.output));
```

### Option C: React component

```jsx
// AIHorizonChat.jsx
import { useState } from 'react';

export function AIHorizonChat() {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    
    const sendMessage = async () => {
        const response = await fetch('https://api.theaihorizon.org/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: input })
        });
        const data = await response.json();
        setMessages([...messages, { role: 'user', content: input }, { role: 'assistant', content: data.output }]);
        setInput('');
    };
    
    return (
        <div className="ai-horizon-chat">
            {/* Your chat UI */}
        </div>
    );
}
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `DCWF_STORE_NAME` | Yes | Gemini File Search store for DCWF data |
| `ARTIFACTS_STORE_NAME` | Yes | Gemini File Search store for artifacts |
| `GEMINI_MODEL` | No | Model to use (default: gemini-2.5-flash) |

## Production Checklist

- [ ] Set proper CORS origins (not "*")
- [ ] Add rate limiting
- [ ] Add authentication if needed
- [ ] Use Redis for session storage
- [ ] Set up monitoring (Sentry, etc.)
- [ ] Enable HTTPS
- [ ] Set up backup for File Search stores
- [ ] Configure logging
