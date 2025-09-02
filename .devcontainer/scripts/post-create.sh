#!/bin/bash

# KireMisu DevContainer Post-Create Script
# This script runs after the development container is created

set -e

echo "🚀 Setting up KireMisu development environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[SETUP]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Wait for PostgreSQL to be ready
log "Waiting for PostgreSQL to be ready..."
until pg_isready -h postgres -p 5432 -U kiremisu; do
    echo "PostgreSQL is not ready yet, waiting..."
    sleep 2
done

log "PostgreSQL is ready!"

# Set up Python backend environment
log "Setting up Python backend environment..."
cd /workspace

if [ -d "backend" ]; then
    cd backend
    
    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        log "Creating Python virtual environment..."
        uv venv
    fi
    
    # Install dependencies
    if [ -f "requirements.txt" ]; then
        log "Installing Python dependencies from requirements.txt..."
        uv pip install -r requirements.txt
    elif [ -f "pyproject.toml" ]; then
        log "Installing Python dependencies from pyproject.toml..."
        uv pip install -e .
    else
        warn "No Python dependencies file found, installing common FastAPI dependencies..."
        uv pip install fastapi uvicorn sqlalchemy asyncpg python-multipart python-jose[cryptography] passlib[bcrypt] structlog httpx pillow pymupdf rarfile
    fi
    
    # Install development dependencies
    log "Installing Python development dependencies..."
    uv pip install pytest pytest-asyncio pytest-cov ruff mypy pre-commit
    
    cd ..
else
    warn "Backend directory not found, skipping Python setup"
fi

# Set up Node.js frontend environment
log "Setting up Node.js frontend environment..."
if [ -d "frontend" ]; then
    cd frontend
    
    if [ -f "package.json" ]; then
        log "Installing Node.js dependencies..."
        pnpm install
    else
        warn "No package.json found, creating a basic Next.js setup..."
        pnpm create next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias="@/*"
    fi
    
    cd ..
else
    warn "Frontend directory not found, skipping Node.js setup"
fi

# Set up Git hooks if pre-commit config exists
if [ -f ".pre-commit-config.yaml" ]; then
    log "Setting up pre-commit hooks..."
    pre-commit install
fi

# Create necessary directories for development
log "Creating necessary directories..."
mkdir -p logs

# Create development manga library structure if using defaults
log "Setting up manga library directories..."

# Create default directories if bind mounts don't exist
if [ ! -d "/manga" ] || [ -z "$(ls -A /manga 2>/dev/null)" ]; then
    log "Creating default manga library structure..."
    mkdir -p /manga
    
    # Create sample manga structure with README
    cat > /manga/README.md << 'EOF'
# Manga Library Directory (Bind Mount)

This directory is bind-mounted from your host system. It supports both reading existing manga and downloading new chapters.

## Directory Structure:
```
/manga/
├── Series Name/
│   ├── Chapter 001 - Chapter Title.cbz
│   ├── Chapter 002 - Another Chapter.cbr
│   └── [new downloads appear here]
├── Another Series/
│   ├── Volume 01/
│   │   ├── Chapter 001.zip
│   │   └── Chapter 002.zip
│   └── [new downloads appear here]
└── ...
```

## Supported Formats:
- .cbz (Comic Book ZIP)
- .cbr (Comic Book RAR)  
- .zip (Standard ZIP)
- .rar (RAR archive)
- .pdf (PDF files)
- Folders with image files

## How It Works:
1. **Scanning**: Application scans this directory and creates metadata in the database
2. **Reading**: Files are served directly from this location  
3. **Downloading**: New chapters are downloaded directly into series folders
4. **Processing**: Thumbnails and metadata are cached separately

## Configuration:
To use your own manga library, set MANGA_LIBRARY_PATH in .env.devcontainer
EOF

    # Create sample series directories for development
    mkdir -p "/manga/Sample Series 1"
    mkdir -p "/manga/Sample Series 2/Volume 01"
    
    echo "Sample chapter file - replace with real manga" > "/manga/Sample Series 1/Chapter 001 - Sample.txt"
    echo "Sample volume chapter - replace with real manga" > "/manga/Sample Series 2/Volume 01/Chapter 001 - Sample.txt"
fi

# Create cache directories
mkdir -p /thumbnails /processed

# Set proper permissions
chmod -R 755 logs 2>/dev/null || true
chmod -R 755 /manga /thumbnails /processed 2>/dev/null || true
chmod +x .devcontainer/scripts/*.sh 2>/dev/null || true

# Create environment files from templates if they exist
if [ -f "backend/.env.example" ] && [ ! -f "backend/.env" ]; then
    log "Creating backend .env file from template..."
    cp backend/.env.example backend/.env
fi

if [ -f "frontend/.env.example" ] && [ ! -f "frontend/.env.local" ]; then
    log "Creating frontend .env.local file from template..."
    cp frontend/.env.example frontend/.env.local
fi

# Create a development README
log "Creating development guide..."
cat > DEV_SETUP.md << 'EOF'
# KireMisu Development Environment

Welcome to the KireMisu development environment! This DevContainer provides a complete setup for developing the full-stack manga library application.

## Quick Start

1. The environment is already set up with:
   - Python 3.12 with uv package manager
   - Node.js 20 with pnpm
   - PostgreSQL 15 database
   - All necessary development tools

2. **Backend Development** (FastAPI):
   ```bash
   cd backend
   # Activate virtual environment
   source .venv/bin/activate
   # Run the development server
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **Frontend Development** (Next.js):
   ```bash
   cd frontend
   # Run the development server
   pnpm dev
   ```

## Database Access

- **Host**: `postgres`
- **Port**: `5432`
- **Database**: `kiremisu`
- **Username**: `kiremisu`
- **Password**: `development`

Access via psql:
```bash
psql -h postgres -p 5432 -U kiremisu -d kiremisu
```

## Available Ports

- **3000**: Frontend (Next.js)
- **8000**: Backend API (FastAPI)
- **5432**: PostgreSQL Database

## Development Commands

### Backend
```bash
# Run tests
pytest

# Format code
ruff format .

# Lint code
ruff check .

# Type checking
mypy .
```

### Frontend
```bash
# Run tests
pnpm test

# Build for production
pnpm build

# Lint and format
pnpm lint
pnpm prettier --write .
```

## File Structure

- `backend/`: FastAPI backend application
- `frontend/`: Next.js frontend application
- `data/`: Development data storage
- `.devcontainer/`: DevContainer configuration

## Environment Variables

Backend environment variables are in `backend/.env`:
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT secret key (change in production)
- `MANGA_LIBRARY_PATH`: Path to manga files (/manga)
- `THUMBNAILS_PATH`: Path to generated thumbnails (/thumbnails)
- `PROCESSED_DATA_PATH`: Path to processed data cache (/processed)

Frontend environment variables are in `frontend/.env.local`:
- `NEXT_PUBLIC_API_URL`: Backend API URL

Enjoy developing KireMisu! 🚀
EOF

# Final setup message
echo ""
echo -e "${GREEN}✅ KireMisu development environment setup complete!${NC}"
echo ""
echo -e "${BLUE}📚 Quick Start:${NC}"
echo -e "  1. Backend: ${YELLOW}cd backend && source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload${NC}"
echo -e "  2. Frontend: ${YELLOW}cd frontend && pnpm dev${NC}"
echo -e "  3. Database: ${YELLOW}psql -h postgres -p 5432 -U kiremisu -d kiremisu${NC}"
echo ""
echo -e "${BLUE}📖 Read DEV_SETUP.md for detailed instructions${NC}"
echo ""
echo -e "${GREEN}Happy coding! 🎉${NC}"