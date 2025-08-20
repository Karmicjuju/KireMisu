# KireMisu Deployment Guide

## Quick Start - Docker Compose

### 1. Create docker-compose.yml
```yaml
version: '3.8'
services:
  backend:
    image: kiremisu/backend:latest
    environment:
      - DATABASE_URL=postgresql://kiremisu:password@postgres:5432/kiremisu
      - MANGADX_API_URL=https://api.mangadx.org
      - JWT_SECRET_KEY=your-secret-key-here
    volumes:
      - ${MANGA_LIBRARY_PATH}:/manga:ro
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      
  frontend:
    image: kiremisu/frontend:latest
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    ports:
      - "3000:3000"
    depends_on:
      - backend
      
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=kiremisu
      - POSTGRES_USER=kiremisu
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

### 2. Deploy
```bash
# Set your manga library path
export MANGA_LIBRARY_PATH=/path/to/your/manga

# Start services
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f backend
```

### 3. Access
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Environment Variables

### Required
```bash
DATABASE_URL=postgresql://user:pass@host:5432/kiremisu
MANGA_LIBRARY_PATH=/manga
JWT_SECRET_KEY=your-secret-key-here  # Generate with: openssl rand -hex 32
```

### Optional
```bash
MANGADX_API_URL=https://api.mangadx.org
MANGADX_API_KEY=your_api_key
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,https://kiremisu.example.com
BCRYPT_ROUNDS=12
```

## Kubernetes Deployment

### 1. Basic Deployment
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: kiremisu

---
# k8s/postgres.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: kiremisu
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15
        env:
        - name: POSTGRES_DB
          value: kiremisu
        - name: POSTGRES_USER
          value: kiremisu
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi

---
# k8s/backend.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: kiremisu
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: kiremisu/backend:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: backend-secret
              key: database-url
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: backend-secret
              key: jwt-secret
        volumeMounts:
        - name: manga-storage
          mountPath: /manga
          readOnly: true
        ports:
        - containerPort: 8000
      volumes:
      - name: manga-storage
        persistentVolumeClaim:
          claimName: manga-pvc
```

### 2. Deploy to Kubernetes
```bash
# Apply configurations
kubectl apply -f k8s/

# Check status
kubectl get pods -n kiremisu
kubectl logs -f deployment/backend -n kiremisu
```

## Production Security Hardening

### 1. HTTPS with Traefik
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  traefik:
    image: traefik:v3.0
    command:
      - "--api.insecure=false"
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.email=your@email.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - letsencrypt:/letsencrypt

  frontend:
    image: kiremisu/frontend:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.frontend.rule=Host(`kiremisu.example.com`)"
      - "traefik.http.routers.frontend.entrypoints=websecure"
      - "traefik.http.routers.frontend.tls.certresolver=letsencrypt"

volumes:
  letsencrypt:
```

### 2. Security Headers
```nginx
# nginx.conf (if using nginx instead of Traefik)
server {
    listen 443 ssl http2;
    server_name kiremisu.example.com;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    location / {
        proxy_pass http://frontend:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Backup & Recovery

### Database Backup
```bash
# Create backup
docker-compose exec postgres pg_dump -U kiremisu kiremisu > backup_$(date +%Y%m%d).sql

# Restore backup
docker-compose exec -T postgres psql -U kiremisu kiremisu < backup_20250816.sql

# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups/kiremisu"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
docker-compose exec postgres pg_dump -U kiremisu kiremisu > $BACKUP_DIR/db_$DATE.sql

# Keep only last 7 days
find $BACKUP_DIR -name "db_*.sql" -mtime +7 -delete
```

### Manga Library Backup
```bash
# Rsync to backup server
rsync -av --progress /manga/ backup_server:/backups/manga/

# Or use rclone for cloud backup
rclone sync /manga/ remote:kiremisu-backup/manga/
```

## Monitoring & Health Checks

### Health Endpoints
```bash
# Check application health
curl http://localhost:8000/health
curl http://localhost:3000/api/health

# Example health response
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "manga_library": "accessible",
  "timestamp": "2025-08-16T10:30:00Z"
}
```

### Prometheus Metrics
```bash
# Metrics endpoint
curl http://localhost:8000/metrics

# Example metrics
kiremisu_series_total 156
kiremisu_chapters_total 2847
kiremisu_api_requests_total{method="GET",endpoint="/api/series"} 1234
kiremisu_file_processing_duration_seconds_bucket{le="1.0"} 95
```

### Docker Health Checks
```yaml
services:
  backend:
    image: kiremisu/backend:latest
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

## Troubleshooting

### Common Issues
```bash
# Check logs
docker-compose logs backend
docker-compose logs postgres
docker-compose logs frontend

# Database connection issues
docker-compose exec postgres psql -U kiremisu -d kiremisu -c "SELECT 1;"

# File permission issues
docker-compose exec backend ls -la /manga

# Reset everything
docker-compose down -v
docker-compose up -d
```

### Performance Tuning
```bash
# PostgreSQL tuning
echo "
shared_buffers = 256MB
effective_cache_size = 1GB
random_page_cost = 1.1
" >> /etc/postgresql/postgresql.conf

# Docker resource limits
docker-compose.yml:
  backend:
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
```

### Log Analysis
```bash
# Backend error patterns
docker-compose logs backend | grep "ERROR"

# API response times
docker-compose logs backend | grep "duration" | tail -20

# Database slow queries
docker-compose logs postgres | grep "slow"
```

For advanced deployment scenarios and GitOps with ArgoCD, see the full kiremisu_tech_stack.md documentation.
