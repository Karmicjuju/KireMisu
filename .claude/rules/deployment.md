# Deployment and Infrastructure Guidelines

## Container Strategy

### Multi-Stage Docker Build
```dockerfile
# Example Dockerfile structure for KireMisu
FROM python:3.11-slim as backend-base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM node:18-alpine as frontend-build
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

FROM backend-base as production
COPY --from=frontend-build /app/dist ./static
COPY . .
EXPOSE 8000
CMD ["uvicorn", "kiremisu.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Container Optimization
- Use multi-stage builds to minimize image size
- Leverage layer caching for dependencies
- Use slim base images where possible
- Implement proper security scanning in CI/CD
- Set non-root user for container execution

## Environment Configuration

### Essential Environment Variables
```bash
# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/kiremisu
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# Library Configuration
LIBRARY_PATHS=/manga:/light-novels:/comics
LIBRARY_SCAN_INTERVAL=3600  # seconds
THUMBNAIL_CACHE_PATH=/app/cache/thumbnails

# External API Configuration
MANGADX_API_URL=https://api.mangadx.org
MANGADX_RATE_LIMIT=5  # requests per second
MANGADX_API_TIMEOUT=30

# Security Configuration
SECRET_KEY=your-secret-key-here
API_KEY_EXPIRY_DAYS=30
CORS_ORIGINS=https://yourdomain.com

# Performance Configuration
WORKER_CONCURRENCY=4
FILE_PROCESSING_THREADS=2
CACHE_TTL=3600

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
SENTRY_DSN=  # Optional error tracking
```

### Configuration Validation
```python
# Example configuration validation
from pydantic import BaseSettings, validator
from typing import List

class Settings(BaseSettings):
    database_url: str
    library_paths: List[str]
    secret_key: str
    mangadx_api_url: str = "https://api.mangadx.org"
    
    @validator('library_paths')
    def validate_library_paths(cls, v):
        for path in v:
            if not os.path.exists(path):
                raise ValueError(f"Library path does not exist: {path}")
        return v
    
    class Config:
        env_file = ".env"
```

## Simple Deployment (Docker Compose)

### Production Docker Compose
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  kiremisu:
    image: kiremisu/app:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://kiremisu:${DB_PASSWORD}@postgres:5432/kiremisu
      - LIBRARY_PATHS=/manga
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ${MANGA_LIBRARY_PATH}:/manga:ro
      - thumbnail_cache:/app/cache
    depends_on:
      - postgres
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=kiremisu
      - POSTGRES_USER=kiremisu
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U kiremisu"]
      interval: 10s
      timeout: 5s
      retries: 5

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ${SSL_CERT_PATH}:/etc/nginx/certs:ro
    depends_on:
      - kiremisu
    restart: unless-stopped

volumes:
  postgres_data:
  thumbnail_cache:
```

### Nginx Configuration
```nginx
# nginx.conf for reverse proxy
events {
    worker_connections 1024;
}

http {
    upstream kiremisu {
        server kiremisu:8000;
    }

    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        ssl_certificate /etc/nginx/certs/fullchain.pem;
        ssl_certificate_key /etc/nginx/certs/privkey.pem;

        client_max_body_size 100M;
        
        location / {
            proxy_pass http://kiremisu;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /api/stream {
            proxy_pass http://kiremisu;
            proxy_buffering off;
            proxy_set_header Connection '';
            proxy_http_version 1.1;
            chunked_transfer_encoding off;
        }
    }
}
```

## Kubernetes Deployment

### Namespace and RBAC
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: kiremisu
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: kiremisu
  namespace: kiremisu
```

### ConfigMap and Secrets
```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: kiremisu-config
  namespace: kiremisu
data:
  MANGADX_API_URL: "https://api.mangadx.org"
  LOG_LEVEL: "INFO"
  LOG_FORMAT: "json"
  WORKER_CONCURRENCY: "4"
---
apiVersion: v1
kind: Secret
metadata:
  name: kiremisu-secrets
  namespace: kiremisu
type: Opaque
stringData:
  DATABASE_URL: "postgresql+asyncpg://user:password@postgres:5432/kiremisu"
  SECRET_KEY: "your-secret-key"
```

### Persistent Volumes
```yaml
# k8s/volumes.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: manga-library
  namespace: kiremisu
spec:
  accessModes:
    - ReadOnlyMany
  resources:
    requests:
      storage: 1Ti
  storageClassName: nfs-client
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-data
  namespace: kiremisu
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 100Gi
  storageClassName: fast-ssd
```

### Application Deployment
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kiremisu
  namespace: kiremisu
spec:
  replicas: 2
  selector:
    matchLabels:
      app: kiremisu
  template:
    metadata:
      labels:
        app: kiremisu
    spec:
      serviceAccountName: kiremisu
      containers:
      - name: kiremisu
        image: kiremisu/app:v1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: kiremisu-secrets
              key: DATABASE_URL
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: kiremisu-secrets
              key: SECRET_KEY
        envFrom:
        - configMapRef:
            name: kiremisu-config
        volumeMounts:
        - name: manga-library
          mountPath: /manga
          readOnly: true
        - name: cache
          mountPath: /app/cache
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: manga-library
        persistentVolumeClaim:
          claimName: manga-library
      - name: cache
        emptyDir: {}
```

### Service and Ingress
```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: kiremisu
  namespace: kiremisu
spec:
  selector:
    app: kiremisu
  ports:
  - port: 80
    targetPort: 8000
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: kiremisu
  namespace: kiremisu
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
spec:
  tls:
  - hosts:
    - manga.yourdomain.com
    secretName: kiremisu-tls
  rules:
  - host: manga.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: kiremisu
            port:
              number: 80
```

### PostgreSQL StatefulSet
```yaml
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
        image: postgres:15-alpine
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
        - name: postgres-data
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
  volumeClaimTemplates:
  - metadata:
      name: postgres-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 100Gi
```

## Monitoring and Observability

### Health Checks
```python
# Health check endpoints
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    try:
        # Check database connectivity
        await db.execute(text("SELECT 1"))
        
        # Check file system access
        library_paths = settings.library_paths
        for path in library_paths:
            if not os.path.exists(path):
                raise HTTPException(500, f"Library path not accessible: {path}")
        
        return {"status": "ready", "checks": {"database": "ok", "filesystem": "ok"}}
    except Exception as e:
        raise HTTPException(500, f"Service not ready: {str(e)}")
```

### Prometheus Metrics
```python
# Example metrics collection
from prometheus_client import Counter, Histogram, Gauge

# Metrics
http_requests_total = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
file_processing_duration = Histogram('file_processing_duration_seconds', 'File processing duration')
active_users = Gauge('active_users_total', 'Number of active users')
library_series_count = Gauge('library_series_total', 'Total number of series in library')

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    
    http_requests_total.labels(
        method=request.method,
        endpoint=request.url.path
    ).inc()
    
    return response
```

### Logging Configuration
```yaml
# Structured logging with Kubernetes metadata
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
data:
  fluent-bit.conf: |
    [INPUT]
        Name tail
        Path /var/log/containers/kiremisu*.log
        Parser docker
        Tag kube.*
        
    [FILTER]
        Name kubernetes
        Match kube.*
        Keep_Log On
        
    [OUTPUT]
        Name elasticsearch
        Match *
        Host elasticsearch
        Port 9200
        Index kiremisu-logs
```

## Backup and Recovery

### Database Backup Strategy
```bash
#!/bin/bash
# backup-database.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="/backups/kiremisu_${DATE}.sql"

# Create backup
pg_dump $DATABASE_URL > $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE

# Upload to cloud storage (optional)
aws s3 cp "${BACKUP_FILE}.gz" s3://your-backup-bucket/database/

# Clean up old backups (keep last 30 days)
find /backups -name "kiremisu_*.sql.gz" -mtime +30 -delete
```

### Kubernetes CronJob for Backups
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: database-backup
  namespace: kiremisu
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:15-alpine
            command:
            - /bin/bash
            - -c
            - |
              pg_dump $DATABASE_URL | gzip > /backup/kiremisu_$(date +%Y%m%d_%H%M%S).sql.gz
            env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: kiremisu-secrets
                  key: DATABASE_URL
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-storage
          restartPolicy: OnFailure
```

## Security Hardening

### Network Policies
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: kiremisu-network-policy
  namespace: kiremisu
spec:
  podSelector:
    matchLabels:
      app: kiremisu
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to: []
    ports:
    - protocol: TCP
      port: 443  # HTTPS for external APIs
```

### Security Context
```yaml
# Security context for containers
securityContext:
  runAsNonRoot: true
  runAsUser: 1001
  runAsGroup: 1001
  fsGroup: 1001
  allowPrivilegeEscalation: false
  capabilities:
    drop:
    - ALL
  readOnlyRootFilesystem: true
  seccompProfile:
    type: RuntimeDefault
```

### Resource Limits and QoS
```yaml
# Resource management for production
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
    ephemeral-storage: "1Gi"
  limits:
    memory: "2Gi"
    cpu: "1000m"
    ephemeral-storage: "5Gi"
```

This deployment guide covers both simple Docker Compose setups for individual users and sophisticated Kubernetes deployments for production environments, ensuring KireMisu can scale from personal use to enterprise deployments.