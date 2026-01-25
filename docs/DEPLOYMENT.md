# Deployment Guide

## Overview

This guide covers deploying the RAG Expert System to production environments.

## Prerequisites

- Python 3.10 or higher
- OpenAI API key
- Server with at least 2GB RAM
- Domain name (optional)

---

## Local Development

### Windows

```batch
# Setup
setup.bat

# Start services
start_all.bat
```

### Linux/Mac

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API key

# Start API
uvicorn api.main:app --host 0.0.0.0 --port 8001 &

# Start Dashboard
streamlit run dashboard/app.py --server.port 8501
```

---

## Production Deployment

### Option 1: Docker (Recommended)

Create `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose ports
EXPOSE 8001 8501

# Start script
CMD ["./start_all.sh"]
```

Create `docker-compose.yml`:

```yaml
version: "3.8"

services:
  api:
    build: .
    ports:
      - "8001:8001"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./data:/app/data
      - ./uploads:/app/uploads
    command: uvicorn api.main:app --host 0.0.0.0 --port 8001

  dashboard:
    build: .
    ports:
      - "8501:8501"
    environment:
      - API_URL=http://api:8001
    depends_on:
      - api
    command: streamlit run dashboard/app.py --server.port 8501
```

Deploy:

```bash
docker-compose up -d
```

---

### Option 2: Cloud Platforms

#### Heroku

```bash
# Install Heroku CLI
heroku login

# Create app
heroku create rag-expert-system

# Set environment variables
heroku config:set OPENAI_API_KEY=your-key

# Deploy
git push heroku main
```

#### AWS EC2

```bash
# SSH to instance
ssh -i key.pem ubuntu@your-instance

# Install Python
sudo apt update
sudo apt install python3.10 python3-pip

# Clone repository
git clone https://github.com/yourusername/rag-expert-system.git
cd rag-expert-system

# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
nano .env  # Add your API key

# Install supervisor for process management
sudo apt install supervisor

# Create supervisor config
sudo nano /etc/supervisor/conf.d/rag-api.conf
```

Supervisor config:

```ini
[program:rag-api]
directory=/home/ubuntu/rag-expert-system
command=/home/ubuntu/rag-expert-system/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8001
user=ubuntu
autostart=true
autorestart=true
stderr_logfile=/var/log/rag-api.err.log
stdout_logfile=/var/log/rag-api.out.log
```

Start services:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start rag-api
```

---

### Option 3: Nginx Reverse Proxy

Install Nginx:

```bash
sudo apt install nginx
```

Configure:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    location /api {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Enable and restart:

```bash
sudo ln -s /etc/nginx/sites-available/rag /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Environment Variables

Production `.env`:

```env
# API Configuration
OPENAI_API_KEY=your-production-key

# Models
EMBEDDING_MODEL=text-embedding-3-large
LLM_MODEL=gpt-4-turbo-preview

# Server
API_HOST=0.0.0.0
API_PORT=8001
STREAMLIT_PORT=8501

# Performance
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K_RESULTS=5
SIMILARITY_THRESHOLD=0.7

# Production Settings
DEBUG=False
```

---

## Security Considerations

1. **API Keys**: Never commit `.env` to version control
2. **HTTPS**: Use SSL certificates in production
3. **Authentication**: Implement user authentication
4. **Rate Limiting**: Add rate limiting to prevent abuse
5. **CORS**: Configure CORS properly for your domain
6. **Input Validation**: Validate all user inputs
7. **File Upload Limits**: Set appropriate file size limits

---

## Monitoring

### Logging

Configure logging in production:

```python
# config/settings.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
```

### Health Checks

Monitor the health endpoint:

```bash
curl http://localhost:8001/health
```

### Metrics

Track key metrics:

- Request count
- Response times
- Error rates
- Document count
- Query performance

---

## Backup and Recovery

### Backup Vector Store

```bash
# Backup data directory
tar -czf backup-$(date +%Y%m%d).tar.gz data/
```

### Restore

```bash
# Extract backup
tar -xzf backup-20260119.tar.gz
```

---

## Scaling

### Horizontal Scaling

Use load balancer with multiple API instances:

```yaml
# docker-compose.yml
services:
  api:
    deploy:
      replicas: 3
    # ... rest of config
```

### Vertical Scaling

Increase resources:

- RAM: 4GB+ for better performance
- CPU: Multi-core for parallel processing
- Storage: SSD for faster vector operations

---

## Troubleshooting

### High Memory Usage

Reduce chunk size or implement pagination:

```env
CHUNK_SIZE=500
TOP_K_RESULTS=3
```

### Slow Queries

Optimize similarity threshold:

```env
SIMILARITY_THRESHOLD=0.8
```

### API Timeouts

Increase timeout settings:

```python
# api/main.py
app = FastAPI(timeout=300)
```

---

## Maintenance

### Regular Tasks

1. **Clean old uploads**: Remove processed files
2. **Monitor logs**: Check for errors
3. **Update dependencies**: Keep packages current
4. **Backup data**: Regular backups
5. **Monitor costs**: Track OpenAI API usage

### Updates

```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart services
sudo supervisorctl restart rag-api
```

---

## Cost Optimization

### OpenAI API Costs

- Use `text-embedding-3-small` instead of `large` (cheaper)
- Implement caching for repeated queries
- Set reasonable `max_tokens` limits
- Monitor usage via OpenAI dashboard

### Infrastructure Costs

- Use spot instances for non-critical workloads
- Implement auto-scaling
- Use CDN for static assets
- Optimize database queries

---

## Support

For deployment issues:

1. Check logs: `logs/app.log`
2. Verify environment variables
3. Test health endpoint
4. Review error messages
5. Consult documentation

---

**Production Checklist:**

- [ ] Environment variables configured
- [ ] SSL certificate installed
- [ ] Firewall rules configured
- [ ] Monitoring setup
- [ ] Backup strategy implemented
- [ ] Error logging configured
- [ ] Performance tested
- [ ] Security audit completed
- [ ] Documentation updated
- [ ] Team trained
