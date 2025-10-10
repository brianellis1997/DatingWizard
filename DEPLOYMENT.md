# Dating Wizard - Deployment Guide

## 🐳 Docker Deployment (Recommended)

### Prerequisites

- Docker Desktop installed
- Docker Compose installed
- 8GB RAM minimum
- 10GB disk space

### Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/brianellis1997/DatingWizard.git
   cd DatingWizard
   ```

2. **Build and start containers**:
   ```bash
   docker-compose up --build
   ```

3. **Access the application**:
   - Frontend: http://localhost
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Container Architecture

```
┌─────────────────────────────────────────┐
│          Nginx (Port 80)                │
│  - Serves React frontend                │
│  - Proxies /api → backend:8000          │
│  - Proxies /uploads → backend:8000      │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      FastAPI Backend (Port 8000)        │
│  - Classification API                   │
│  - Preference management                │
│  - SQLite database                      │
│  - File uploads                         │
└─────────────────────────────────────────┘
```

### Docker Commands

```bash
# Start containers
docker-compose up -d

# Stop containers
docker-compose down

# View logs
docker-compose logs -f

# Rebuild after code changes
docker-compose up --build

# Reset everything (WARNING: deletes data)
docker-compose down -v
rm -rf data/ uploads/
docker-compose up --build
```

### Persistent Data

The following directories are mounted as volumes:
- `./config` - User preferences and reference images
- `./data` - SQLite database
- `./uploads` - Uploaded screenshots and images
- `./logs` - Application logs

These persist across container restarts.

## 💻 Local Development

### Backend

1. **Create virtual environment**:
   ```bash
   python3 -m venv wizard
   source wizard/bin/activate  # or `wizard\Scripts\activate` on Windows
   ```

2. **Install dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   pip install -r requirements.txt
   ```

3. **Install Tesseract OCR**:
   ```bash
   # macOS
   brew install tesseract

   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr

   # Windows
   # Download from: https://github.com/UB-Mannheim/tesseract/wiki
   ```

4. **Run backend**:
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

   Backend will be available at: http://localhost:8000

### Frontend

1. **Install dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Configure API URL**:
   ```bash
   cp .env.example .env
   # Edit .env if needed (default: http://localhost:8000/api)
   ```

3. **Run development server**:
   ```bash
   npm run dev
   ```

   Frontend will be available at: http://localhost:5173

## 🚀 Production Deployment

### Option 1: Docker on a Server

1. **Setup server** (Ubuntu 22.04 recommended):
   ```bash
   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh

   # Install Docker Compose
   sudo apt-get install docker-compose-plugin
   ```

2. **Clone and deploy**:
   ```bash
   git clone https://github.com/brianellis1997/DatingWizard.git
   cd DatingWizard
   docker-compose up -d
   ```

3. **Setup domain** (optional):
   - Point your domain to server IP
   - Update `nginx-frontend.conf` with your domain
   - Add SSL with Let's Encrypt

### Option 2: Manual Deployment

1. **Backend**:
   ```bash
   # Install dependencies
   pip install -r backend/requirements.txt -r requirements.txt

   # Run with gunicorn
   gunicorn backend.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
   ```

2. **Frontend**:
   ```bash
   # Build
   cd frontend
   npm run build

   # Serve with nginx
   sudo cp -r dist/* /var/www/html/
   ```

### Environment Variables

Create `.env` in project root:

```bash
# Backend
DATABASE_URL=sqlite:///./data/dating_wizard.db
DEBUG=False

# Frontend (frontend/.env)
VITE_API_URL=https://your-domain.com/api
```

## 🔧 Configuration

### Backend Configuration

Edit `backend/config.py`:

```python
# API
API_V1_PREFIX = "/api"

# CORS (add your domain)
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://your-domain.com",
]

# File Upload
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
```

### Nginx Configuration

For custom domain, edit `nginx-frontend.conf`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    # ... rest of config
}
```

## 📊 Monitoring

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Frontend
curl http://localhost/
```

### Logs

```bash
# Docker logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Local logs
tail -f logs/dating_wizard_*.log
```

## 🔐 Security Considerations

### Production Checklist

- [ ] Change `DEBUG=False` in production
- [ ] Use HTTPS with SSL certificate
- [ ] Set strong CORS origins
- [ ] Implement rate limiting
- [ ] Regular backups of `data/` directory
- [ ] Keep dependencies updated
- [ ] Monitor logs for errors
- [ ] Use environment-specific `.env` files
- [ ] Restrict file upload sizes
- [ ] Implement authentication (if multi-user)

### SSL Setup with Let's Encrypt

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo certbot renew --dry-run
```

## 🐛 Troubleshooting

### Backend Won't Start

1. **Check Python version**:
   ```bash
   python --version  # Should be 3.9+
   ```

2. **Check dependencies**:
   ```bash
   pip install -r backend/requirements.txt -r requirements.txt
   ```

3. **Check Tesseract**:
   ```bash
   tesseract --version
   ```

4. **Check database**:
   ```bash
   ls -la data/dating_wizard.db
   # If corrupted, delete and restart
   ```

### Frontend Build Errors

1. **Clear node_modules**:
   ```bash
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   ```

2. **Check Node version**:
   ```bash
   node --version  # Should be 18+
   ```

3. **Build verbose**:
   ```bash
   npm run build -- --debug
   ```

### Docker Issues

1. **Port conflicts**:
   ```bash
   # Check what's using port 80/8000
   lsof -i :80
   lsof -i :8000
   ```

2. **Reset Docker**:
   ```bash
   docker-compose down -v
   docker system prune -a
   docker-compose up --build
   ```

3. **Memory issues**:
   - Increase Docker memory limit (Settings → Resources)
   - Minimum 8GB recommended

### API Connection Errors

1. **Check CORS settings** in `backend/config.py`
2. **Verify API URL** in `frontend/.env`
3. **Check network** in `docker-compose.yml`

## 📦 Backup & Restore

### Backup

```bash
# Backup data directory
tar -czf backup-$(date +%Y%m%d).tar.gz data/ config/ uploads/

# Backup database only
cp data/dating_wizard.db backups/dating_wizard-$(date +%Y%m%d).db
```

### Restore

```bash
# Restore from backup
tar -xzf backup-20241009.tar.gz

# Restart containers
docker-compose restart
```

## 🔄 Updates

### Update Application

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose up --build -d
```

### Update Dependencies

```bash
# Backend
pip install -r backend/requirements.txt --upgrade

# Frontend
cd frontend
npm update
```

## 📞 Support

For deployment issues:
1. Check logs: `docker-compose logs -f`
2. Review this documentation
3. Check GitHub issues
4. Verify system requirements

## 🎯 Performance Optimization

### Production Settings

1. **Enable caching** in nginx
2. **Use production build** for frontend
3. **Optimize database** queries
4. **Enable compression** (gzip)
5. **Use CDN** for static assets (optional)

### Scaling

For high traffic:
- Add load balancer
- Run multiple backend instances
- Use PostgreSQL instead of SQLite
- Implement Redis caching
- Use S3 for file storage

## ✅ Quick Reference

```bash
# Start everything
docker-compose up -d

# Stop everything
docker-compose down

# View logs
docker-compose logs -f

# Restart service
docker-compose restart backend

# Access at
http://localhost          # Frontend
http://localhost:8000     # Backend
http://localhost:8000/docs  # API Docs
```

---

**Need help?** Check the [PROTOTYPE_GUIDE.md](PROTOTYPE_GUIDE.md) for usage instructions.
