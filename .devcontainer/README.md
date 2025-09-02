# KireMisu Development Container

This directory contains the DevContainer configuration for the KireMisu manga library application. The DevContainer provides a complete, portable development environment that works consistently across different machines.

## What's Included

### Services
- **Main Development Container**: Python 3.12 + Node.js 20 environment
- **PostgreSQL 15**: Database with sample data
- **VS Code Extensions**: Pre-configured for full-stack development

### Development Tools
- **Python**: uv package manager, FastAPI, SQLAlchemy
- **Node.js**: pnpm, Next.js, TypeScript, Tailwind CSS
- **Database**: PostgreSQL with pgAdmin-like extensions
- **Linting**: Ruff (Python), ESLint/Prettier (TypeScript)
- **Testing**: pytest (Python), Vitest (TypeScript)

## Quick Start

### Prerequisites
- [Visual Studio Code](https://code.visualstudio.com/)
- [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### Getting Started

1. **Open in DevContainer**:
   - Open this project in VS Code
   - When prompted, click "Reopen in Container"
   - Or use `Ctrl+Shift+P` → "Dev Containers: Reopen in Container"

2. **Wait for Setup**:
   - The container will build and install dependencies
   - This may take 5-10 minutes on first run
   - Subsequent starts will be much faster

3. **Start Development**:
   ```bash
   # Backend (FastAPI)
   cd backend
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   
   # Frontend (Next.js) - in another terminal
   cd frontend  
   pnpm dev
   ```

## Container Architecture

### File Structure
```
.devcontainer/
├── devcontainer.json       # Main configuration
├── docker-compose.yml      # Multi-service setup
├── Dockerfile.backend      # Python development environment
├── Dockerfile.frontend     # Node.js development environment
├── scripts/
│   ├── init-db.sql        # Database initialization
│   ├── post-create.sh     # Setup script
│   └── post-start.sh      # Startup script
└── README.md              # This file
```

### Port Forwarding
- **3000**: Frontend development server (Next.js)
- **8000**: Backend API server (FastAPI)
- **5432**: PostgreSQL database

### Volume Mounts
- **Source code**: Mounted as `/workspace` with cached consistency
- **Node modules**: Separate volume for faster installs
- **UV cache**: Python package cache for faster installs
- **PostgreSQL data**: Persistent database storage
- **Manga library**: Bind mount at `/manga` (read-write for downloads)
- **Thumbnails**: Bind mount at `/thumbnails` (generated cache)
- **Processed data**: Bind mount at `/processed` (metadata cache)

## Database Setup

The PostgreSQL database is automatically initialized with:
- **Database**: `kiremisu`
- **User**: `kiremisu` 
- **Password**: `development`
- **Sample data**: Basic series and chapter tables with test records

### Connecting to Database
```bash
# Via psql
psql -h postgres -p 5432 -U kiremisu -d kiremisu

# Via environment variable
DATABASE_URL=postgresql://kiremisu:development@postgres:5432/kiremisu
```

## Development Workflow

### Backend Development (Python/FastAPI)
```bash
cd backend

# Install dependencies
uv pip install -r requirements.txt

# Run development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run tests
pytest

# Format and lint
ruff format .
ruff check .

# Type checking
mypy .
```

### Frontend Development (TypeScript/Next.js)
```bash
cd frontend

# Install dependencies  
pnpm install

# Run development server
pnpm dev

# Build for production
pnpm build

# Run tests
pnpm test

# Lint and format
pnpm lint
pnpm prettier --write .
```

## Environment Variables

### Backend (.env)
```bash
DATABASE_URL=postgresql://kiremisu:development@postgres:5432/kiremisu
SECRET_KEY=development-secret-key-change-in-production
LOG_LEVEL=DEBUG
PYTHONPATH=/workspace/backend

# Manga library paths (mounted volumes)
MANGA_LIBRARY_PATH=/manga
THUMBNAILS_PATH=/thumbnails  
PROCESSED_DATA_PATH=/processed
```

### Frontend (.env.local)
```bash
NODE_ENV=development
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## VS Code Extensions

The following extensions are automatically installed:

### Python Development
- Python
- Ruff (linting and formatting)
- MyPy Type Checker

### TypeScript/JavaScript Development  
- TypeScript and JavaScript Language Features
- ESLint
- Prettier
- Tailwind CSS IntelliSense

### Database
- PostgreSQL

### General Development
- GitLens
- Docker
- REST Client
- Auto Rename Tag
- Path Intellisense

## Troubleshooting

### Container Won't Start
- Ensure Docker Desktop is running
- Check available disk space (need ~2GB)
- Try rebuilding: `Ctrl+Shift+P` → "Dev Containers: Rebuild Container"

### Database Connection Issues
```bash
# Check PostgreSQL status
pg_isready -h postgres -p 5432 -U kiremisu

# Restart database service
docker compose -f .devcontainer/docker-compose.yml restart postgres
```

### Python Environment Issues
```bash
# Recreate virtual environment
rm -rf backend/.venv
cd backend && uv venv && uv pip install -r requirements.txt
```

### Node.js Dependencies Issues
```bash
# Clear cache and reinstall
rm -rf frontend/node_modules
cd frontend && pnpm install
```

## Customization

### Adding Python Packages
```bash
cd backend
uv pip install package-name
# Add to requirements.txt
```

### Adding Node.js Packages  
```bash
cd frontend
pnpm add package-name
```

### Adding VS Code Extensions
Edit `.devcontainer/devcontainer.json`:
```json
"extensions": [
  "existing.extensions",
  "new.extension.id"
]
```

## Production Differences

The DevContainer is optimized for development with:
- Debug logging enabled
- Hot reloading for both backend and frontend
- Development database with sample metadata
- Manga library volume mounts for file access
- Relaxed security settings

For production deployment, use the Docker files in the `/docker` directory instead.

## Support

For issues with the DevContainer setup:
1. Check this README for common solutions
2. Review the setup logs in VS Code terminal
3. Try rebuilding the container
4. Check Docker Desktop resources (memory/disk)

### Manga Library Setup

The DevContainer uses **bind mounts** to directly access your host manga library, enabling both reading existing manga and downloading new chapters.

#### Option 1: Use Environment Variables (Recommended)

Copy and customize the environment template:
```bash
# Copy the template
cp .env.devcontainer.example .env.devcontainer

# Edit with your paths
# .env.devcontainer
MANGA_LIBRARY_PATH=/path/to/your/manga/library
THUMBNAILS_PATH=/path/to/thumbnails/cache
PROCESSED_DATA_PATH=/path/to/processed/cache
```

#### Option 2: Default Development Directories

If no environment variables are set, the container will create and use:
- `./dev-manga/` - Your manga library
- `./dev-thumbnails/` - Thumbnail cache  
- `./dev-processed/` - Processed metadata cache

#### Expected Directory Structure:
```
/your/manga/library/
├── One Piece/
│   ├── Chapter 001 - Romance Dawn.cbz
│   ├── Chapter 002 - Buggy the Clown.cbr
│   └── [new downloads will appear here]
├── Naruto/
│   ├── Chapter 001 - Uzumaki Naruto!!.zip
│   └── [new downloads will appear here]  
└── Attack on Titan/
    ├── Volume 01/
    │   ├── Chapter 001.pdf
    │   └── Chapter 002.pdf
    └── [new downloads will appear here]
```

#### Supported Formats:
- `.cbz` (Comic Book ZIP)
- `.cbr` (Comic Book RAR)
- `.zip` (Standard ZIP archive)
- `.rar` (RAR archive)
- `.pdf` (PDF files)
- Folders with image files

The application will:
- **Scan** existing files and create metadata in the database
- **Download** new chapters directly into the appropriate series folders
- **Generate** thumbnails in the cache directory
- **Keep** all original files in place (no database storage)

For application-specific issues, refer to the main project documentation.