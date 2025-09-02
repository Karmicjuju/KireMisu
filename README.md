# KireMisu

A modern, full-stack manga library management application built with FastAPI and Next.js.

## Features

- **Library Management**: Organize and browse your manga collection
- **Reading Interface**: Built-in manga reader with multiple viewing modes
- **Watch Lists**: Track series and get notified of new chapters
- **File Support**: Supports CBZ, CBR, ZIP, RAR, PDF, and folder formats
- **Metadata Management**: Automatic series and chapter detection
- **Responsive Design**: Works on desktop and mobile devices

## Architecture

- **Backend**: FastAPI with PostgreSQL
- **Frontend**: Next.js with TypeScript and Tailwind CSS
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Containerization**: Docker and Docker Compose
- **Development**: DevContainer support for consistent environments

## Quick Start

### Using DevContainer (Recommended)

1. Open the project in VS Code
2. Install the Dev Containers extension
3. Click "Reopen in Container" when prompted
4. Wait for the setup to complete

### Manual Setup

1. Clone the repository
2. Copy environment files:
   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env.local
   ```
3. Start with Docker Compose:
   ```bash
   docker-compose up -d
   ```

## Development

### Backend (FastAPI)

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend (Next.js)

```bash
cd frontend
pnpm install
pnpm dev
```

### Database

Access PostgreSQL:
```bash
psql -h localhost -p 5432 -U kiremisu -d kiremisu
```

## Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Tests
```bash
cd frontend
pnpm test
```

## Production Deployment

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## License

See [LICENSE](LICENSE) file for details.