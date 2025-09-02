# KireMisu Quick Reference

Quick command reference and essential information for KireMisu development.

## 🚀 Development Commands

### Backend (Python)

```bash
# Environment Setup
uv venv                              # Create virtual environment
source .venv/bin/activate            # Activate virtual environment (Linux/Mac)
# or
.venv\Scripts\activate               # Activate virtual environment (Windows)
uv pip install -r requirements.txt  # Install dependencies

# Development Server
uv run fastapi dev app/main.py       # Start development server
uv run fastapi dev app/main.py --port 8001  # Custom port

# Testing
uv run pytest                       # Run all tests
uv run pytest tests/unit/          # Run unit tests only
uv run pytest tests/integration/   # Run integration tests only
uv run pytest --cov=app           # Run with coverage
uv run pytest -v --tb=short       # Verbose with short traceback

# Code Quality
uv run ruff check .                # Lint code
uv run ruff format .               # Format code
uv run ruff check --fix .          # Lint and auto-fix
uv run mypy app/                   # Type checking

# Database
uv run python scripts/init_db.py   # Initialize database
uv run python scripts/seed_data.py # Seed test data
```

### Frontend (Node.js)

```bash
# Dependencies
pnpm install                        # Install dependencies
pnpm add <package>                  # Add dependency
pnpm add -D <package>               # Add dev dependency

# Development Server
pnpm dev                           # Start development server
pnpm dev --port 3001               # Custom port
pnpm build                         # Build for production
pnpm start                         # Start production server

# Testing
pnpm test                          # Run unit tests
pnpm test:watch                    # Run tests in watch mode
pnpm test:coverage                 # Run tests with coverage
pnpm test:e2e                      # Run E2E tests
pnpm playwright test               # Run Playwright tests
pnpm playwright test --ui          # Run with UI mode

# Code Quality
pnpm lint                          # Lint code
pnpm lint:fix                      # Lint and auto-fix
pnpm format                        # Format code
pnpm type-check                    # TypeScript type checking
```

### Docker Commands

```bash
# Development Environment
docker-compose up                   # Start all services
docker-compose up -d               # Start in background
docker-compose down                # Stop all services
docker-compose logs backend        # View backend logs
docker-compose exec backend bash   # Shell into backend container

# Production Environment
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml down

# Database Management
docker-compose exec postgres psql -U kiremisu -d kiremisu
docker-compose exec postgres pg_dump -U kiremisu kiremisu > backup.sql

# Rebuild Services
docker-compose build               # Rebuild all images
docker-compose build backend       # Rebuild specific service
docker-compose up --build          # Rebuild and start
```

### Git Commands

```bash
# Development Workflow
git checkout -b feature/my-feature  # Create feature branch
git add .                          # Stage changes
git commit -m "feat: add new feature"  # Commit with conventional format
git push -u origin feature/my-feature  # Push branch

# Pre-commit Setup
pre-commit install                 # Install pre-commit hooks
pre-commit run --all-files         # Run hooks on all files
```

## 📁 Key File Locations

### Configuration Files

```bash
# Backend
backend/pyproject.toml             # Python project config
backend/requirements.txt           # Python dependencies
backend/.env                       # Environment variables

# Frontend
frontend/package.json              # Node.js dependencies
frontend/tsconfig.json             # TypeScript config
frontend/next.config.js            # Next.js config
frontend/.env.local                # Environment variables

# Docker
docker-compose.yml                 # Development environment
docker-compose.prod.yml            # Production environment
```

### Application Entry Points

```bash
# Backend
backend/app/main.py                # FastAPI application
backend/app/api/v1/router.py       # API router

# Frontend
frontend/src/app/layout.tsx        # Root layout
frontend/src/app/page.tsx          # Home page
```

## 🌐 Default URLs & Ports

### Development

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Database**: localhost:5432

### API Endpoints

```bash
# Base URL
http://localhost:8000/api/v1

# Series Endpoints
GET    /series                     # List all series
GET    /series/{id}                # Get series by ID
POST   /series                     # Create series
PUT    /series/{id}                # Update series
DELETE /series/{id}                # Delete series

# Chapter Endpoints  
GET    /series/{id}/chapters        # Get series chapters
GET    /chapters/{id}               # Get chapter by ID
POST   /chapters                    # Create chapter

# Watching Endpoints
GET    /watched-series              # Get watched series
POST   /watched-series              # Add to watch list
DELETE /watched-series/{id}         # Remove from watch list

# Authentication
POST   /auth/login                  # Login
POST   /auth/logout                 # Logout
GET    /auth/me                     # Get current user
```

## 🔧 Environment Variables

### Backend (.env)

```bash
# Database
DATABASE_URL=postgresql://kiremisu:password@localhost/kiremisu
DATABASE_POOL_SIZE=20

# Security
SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# External APIs
MANGADX_API_URL=https://api.mangadx.org
MANGADX_RATE_LIMIT=5

# Storage
STORAGE_PATH=/data/manga
THUMBNAIL_PATH=/data/thumbnails
MAX_FILE_SIZE=100MB

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Frontend (.env.local)

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Features
NEXT_PUBLIC_ENABLE_ANALYTICS=false
NEXT_PUBLIC_ENABLE_PWA=true
NEXT_PUBLIC_MAX_UPLOAD_SIZE=100

# External Services
NEXT_PUBLIC_SENTRY_DSN=
```

## 🗃️ Database Schema Quick Reference

### Core Tables

```sql
-- Series table
CREATE TABLE series (
    id UUID PRIMARY KEY,
    title VARCHAR NOT NULL,
    author VARCHAR,
    description TEXT,
    status VARCHAR,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Chapters table
CREATE TABLE chapters (
    id UUID PRIMARY KEY,
    series_id UUID REFERENCES series(id),
    title VARCHAR,
    chapter_number DECIMAL,
    file_path VARCHAR,
    page_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Watch list table
CREATE TABLE watched_series (
    id UUID PRIMARY KEY,
    series_id UUID REFERENCES series(id),
    user_id UUID,
    last_checked TIMESTAMP,
    notification_enabled BOOLEAN DEFAULT true
);
```

## 📊 Testing Commands Quick Reference

### Backend Testing

```bash
# Run specific test file
uv run pytest tests/unit/test_series.py

# Run tests with specific markers
uv run pytest -m "not slow"       # Skip slow tests
uv run pytest -m integration      # Only integration tests

# Debug tests
uv run pytest --pdb               # Drop to debugger on failure
uv run pytest -s                  # Show print statements
uv run pytest --lf                # Run last failed tests

# Coverage
uv run pytest --cov=app --cov-report=html  # HTML coverage report
uv run pytest --cov=app --cov-report=term  # Terminal coverage
```

### Frontend Testing

```bash
# Unit tests
pnpm test                          # Run all unit tests
pnpm test SeriesCard               # Run specific test
pnpm test --coverage               # With coverage

# E2E tests
pnpm playwright test               # Run all E2E tests
pnpm playwright test library       # Run specific test file
pnpm playwright test --debug       # Debug mode
pnpm playwright show-report        # Show test results
```

## 🐛 Debugging Commands

### Backend Debugging

```bash
# Start with debugger
uv run python -m debugpy --listen 5678 --wait-for-client -m fastapi dev app/main.py

# Database debugging
uv run python -c "from app.db.session import engine; print(engine.url)"

# Check environment
uv run python -c "from app.core.config import settings; print(settings)"
```

### Frontend Debugging

```bash
# Build analysis
pnpm build --analyze               # Analyze bundle size
pnpm build --debug                 # Debug build

# Type checking
pnpm tsc --noEmit                  # Check types without building
```

## 📦 Package Management

### Backend Dependencies

```bash
# Add dependency
echo "package-name>=1.0.0" >> requirements.txt
uv pip install -r requirements.txt

# Development dependencies
echo "package-name>=1.0.0" >> requirements-dev.txt
uv pip install -r requirements-dev.txt

# Update dependencies
uv pip list --outdated             # Check for updates
uv pip install --upgrade package-name  # Update specific package
```

### Frontend Dependencies

```bash
# Add dependencies
pnpm add package-name              # Runtime dependency
pnpm add -D package-name           # Development dependency
pnpm add -O package-name           # Optional dependency

# Update dependencies
pnpm outdated                      # Check for updates
pnpm update                        # Update all packages
pnpm update package-name           # Update specific package

# Clean installation
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

## 🚨 Troubleshooting

### Common Issues

```bash
# Backend issues
# Port already in use
lsof -ti:8000 | xargs kill -9     # Kill process on port 8000

# Database connection issues
docker-compose restart postgres    # Restart PostgreSQL
docker-compose logs postgres       # Check PostgreSQL logs

# Python environment issues
uv venv --clear                   # Recreate virtual environment
uv pip install --force-reinstall -r requirements.txt

# Frontend issues
# Port already in use
lsof -ti:3000 | xargs kill -9     # Kill process on port 3000

# Node modules issues
rm -rf node_modules .next         # Clean build artifacts
pnpm install                      # Reinstall dependencies

# TypeScript issues
pnpm tsc --incremental false      # Disable incremental compilation
rm -rf .next                      # Clear Next.js cache
```

### Performance Debugging

```bash
# Backend profiling
uv run python -m cProfile -o profile.prof app/main.py

# Database query analysis
EXPLAIN ANALYZE SELECT * FROM series WHERE title ILIKE '%search%';

# Frontend performance
pnpm build && pnpm start          # Test production build
pnpm lighthouse http://localhost:3000  # Lighthouse audit
```

## 📚 Documentation Links

- **API Documentation**: http://localhost:8000/docs (when running)
- **Project Structure**: [kiremisu_project_structure.md](kiremisu_project_structure.md)
- **Architecture Patterns**: [kiremisu_architecture_patterns.md](kiremisu_architecture_patterns.md)
- **Development Standards**: [kiremisu_development_standards.md](kiremisu_development_standards.md)
- **Implementation Checklist**: [kiremisu_implementation_checklist.md](kiremisu_implementation_checklist.md)