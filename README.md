# KireMisu

A self-hosted, cloud-first manga reader and library management system built with FastAPI and Next.js.

## 🚧 Development Status

KireMisu is currently in Phase 0 - Initial Setup. The repository contains the foundational architecture and development environment setup.

## 📋 Features (Planned)

- **📚 Library Management**: Organize and manage your manga collection with rich metadata
- **🔍 MangaDx Integration**: Search, import, and track manga from MangaDx
- **📖 Reading Experience**: Modern web-based manga reader with annotations
- **🏷️ Custom Organization**: Tags, lists, and advanced filtering
- **👀 Watching System**: Track new chapter releases automatically
- **🔄 File Organization**: Bulk renaming and file management tools
- **🌐 API Access**: RESTful API for automation and integrations
- **🐳 Self-Hosted**: Docker-based deployment for complete control

## 🏗️ Architecture

- **Backend**: FastAPI + Python 3.13+ with async performance
- **Frontend**: Next.js 14+ + TypeScript with SSR
- **Database**: PostgreSQL 16+ with JSONB for flexible metadata
- **File Processing**: PIL + PyMuPDF + rarfile for manga formats
- **Background Jobs**: PostgreSQL-based job queue
- **Development**: Modern tooling with Ruff, UV, and pre-commit hooks

## 🚀 Quick Start (Development)

### Prerequisites

- Python 3.13+
- Node.js 18+
- PostgreSQL 16+ (or use Docker)
- Docker & Docker Compose (optional but recommended)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd KireMisu
   ```

2. **Set up the development environment**
   ```bash
   ./scripts/dev.sh setup
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start with Docker (Recommended)**
   ```bash
   ./scripts/dev.sh docker-dev
   ```

   Or start services individually:
   ```bash
   # Terminal 1: Database
   ./scripts/dev.sh db-setup
   ./scripts/dev.sh db-migrate

   # Terminal 2: Backend
   ./scripts/dev.sh backend

   # Terminal 3: Frontend
   ./scripts/dev.sh frontend
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/api/docs

## 🛠️ Development Commands

Use the development helper script for common tasks:

```bash
# Setup everything
./scripts/dev.sh setup

# Start services
./scripts/dev.sh backend     # Start backend server
./scripts/dev.sh frontend    # Start frontend server
./scripts/dev.sh docker-dev  # Start with Docker Compose

# Database operations
./scripts/dev.sh db-setup    # Setup PostgreSQL database
./scripts/dev.sh db-migrate  # Run migrations
./scripts/dev.sh db-reset    # Reset database (drops all data)

# Code quality
./scripts/dev.sh lint        # Run linting
./scripts/dev.sh format      # Format code
./scripts/dev.sh test        # Run tests

# Docker management
./scripts/dev.sh docker-stop    # Stop Docker development environment
./scripts/dev.sh docker-clean   # Clean up all KireMisu containers
./scripts/dev.sh docker-reset   # Clean containers and start fresh

# Troubleshooting
./scripts/dev.sh ports          # Check and handle port conflicts
./scripts/dev.sh clean          # Clean build artifacts
```

### 🔧 Development Workflows

For common development scenarios, use the workflow helper:

```bash
# Start completely fresh (recommended after tests)
./scripts/dev-workflow.sh fresh-start

# Run tests with automatic cleanup
./scripts/dev-workflow.sh test-cleanup

# Restart development environment (handles port conflicts)
./scripts/dev-workflow.sh restart-dev

# Emergency stop all containers and free ports
./scripts/dev-workflow.sh emergency-stop

# Check status of all services
./scripts/dev-workflow.sh status
```

## 📁 Project Structure

```
KireMisu/
├── backend/                 # FastAPI backend
│   ├── kiremisu/           # Main application package
│   │   ├── core/           # Core configuration and utilities
│   │   ├── database/       # Database models and connections
│   │   ├── api/            # API routes and endpoints (future)
│   │   └── services/       # Business logic services (future)
│   ├── alembic/            # Database migrations
│   └── tests/              # Backend tests (future)
├── frontend/               # Next.js frontend
│   ├── src/
│   │   ├── app/            # Next.js app directory
│   │   ├── components/     # React components (future)
│   │   ├── lib/            # Utility functions
│   │   └── stores/         # Zustand stores (future)
│   └── public/             # Static assets (future)
├── docs/                   # Project documentation
├── scripts/                # Development and deployment scripts
├── docker-compose.yml      # Production Docker setup
├── docker-compose.dev.yml  # Development Docker setup
└── pyproject.toml          # Python project configuration
```

## 🔧 Configuration

### Environment Variables

Key environment variables (see `.env.example` for full list):

- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT secret key for authentication
- `MANGA_STORAGE_PATHS`: JSON array of manga library paths
- `MANGADX_API_URL`: MangaDx API endpoint
- `DEBUG`: Enable debug mode for development

### Storage Setup

Configure manga library paths in your `.env` file:

```bash
MANGA_STORAGE_PATHS=["/path/to/your/manga/library"]
```

In Docker deployments, mount your manga directories as volumes.

## 🚨 Troubleshooting

### Port Conflicts
If you get "port already in use" errors:

```bash
# Check what's using the ports
./scripts/dev-workflow.sh status

# Handle port conflicts automatically
./scripts/dev.sh ports

# Nuclear option - stop everything
./scripts/dev-workflow.sh emergency-stop
```

### Container Issues
If containers won't start or behave unexpectedly:

```bash
# Clean restart
./scripts/dev-workflow.sh restart-dev

# Complete fresh start (recommended)
./scripts/dev-workflow.sh fresh-start

# Manual cleanup
./scripts/dev.sh docker-clean
docker system prune -f  # Clean up Docker system
```

### Database Issues
If database connections fail:

```bash
# Check if PostgreSQL is running
./scripts/dev-workflow.sh status

# Reset database completely
./scripts/dev.sh db-reset

# Manual database check
docker exec -it kiremisu-postgres-dev psql -U kiremisu -d kiremisu
```

### Development Environment Issues
If the development environment seems broken:

```bash
# Fresh start with full cleanup
./scripts/dev-workflow.sh fresh-start

# Reset everything including dependencies
./scripts/dev.sh clean
./scripts/dev.sh setup
./scripts/dev.sh docker-dev
```

## 🐳 Docker Deployment

### Development
```bash
docker-compose -f docker-compose.dev.yml up
```

### Production
```bash
docker-compose up -d
```

### Kubernetes
Kubernetes manifests will be provided in future releases for cloud-native deployments.

## 🧪 Testing

### Running Tests

```bash
# All tests with overall coverage
./scripts/dev.sh test

# Frontend E2E tests
./scripts/dev.sh test-e2e

# Backend only (without dev script)
cd backend && pytest

# Frontend type checking
cd frontend && npm run type-check
```

### Coverage Reports by Test Suite

Generate separate coverage reports for different test types:

```bash
# Unit tests only → htmlcov/unit/
./scripts/dev.sh test-coverage-unit

# Integration tests only → htmlcov/integration/
./scripts/dev.sh test-coverage-integration

# API endpoint tests → htmlcov/api/
./scripts/dev.sh test-coverage-api

# Security tests → htmlcov/security/
./scripts/dev.sh test-coverage-security

# All tests combined → htmlcov/combined/
./scripts/dev.sh test-coverage-all

# Generate comparison report → htmlcov/comparison/
./scripts/dev.sh test-coverage-compare
```

### Coverage Analysis Benefits

- **Unit Test Coverage**: See which modules have isolated test coverage
- **Integration Coverage**: Identify component interaction coverage
- **API Coverage**: Track endpoint-specific test coverage
- **Security Coverage**: Monitor security-focused test coverage
- **Coverage Overlap**: Find redundant or missing coverage areas

## 📋 Roadmap

The project follows a phased development approach:

- **Phase 0**: ✅ Repository setup and development environment
- **Phase 1**: 🚧 Core database schema and basic API endpoints
- **Phase 2**: 📚 Library management and file processing
- **Phase 3**: 🔍 MangaDx integration and metadata enrichment
- **Phase 4**: 📖 Reading interface and user experience
- **Phase 5**: 🏷️ Advanced features and automation

See `docs/kiremisu_prd.md` for detailed feature specifications.

## 🤝 Contributing

KireMisu is currently in early development. Contribution guidelines will be established as the project matures.

### Development Setup for Contributors

1. Fork the repository
2. Follow the setup instructions above
3. Create a feature branch
4. Make your changes with tests
5. Run `./scripts/dev.sh lint` and `./scripts/dev.sh test`
6. Submit a pull request

## 📄 License

[License details to be determined]

## 📞 Support

For questions, issues, or feature requests:

- Open an issue on GitHub
- Check the documentation in `docs/`
- Review the PRD in `docs/kiremisu_prd.md`

---

**Note**: This project is in active development. APIs and features may change rapidly during the initial development phases.