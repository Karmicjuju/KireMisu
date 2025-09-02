# KireMisu Project Structure

This document defines the complete project structure and organization for the KireMisu application.

## Root Directory Structure

```
kiremisu/
├── backend/                 # FastAPI backend application
├── frontend/                # Next.js frontend application
├── docker/                  # Docker configuration files
├── scripts/                 # Development and deployment scripts
├── docs/                    # Additional documentation
├── .claude/                 # Claude-specific documentation
│   └── docs/               # Technical reference documents
├── .github/                 # GitHub configuration
│   ├── workflows/          # GitHub Actions CI/CD
│   └── ISSUE_TEMPLATE/     # Issue templates
├── .vscode/                 # VS Code workspace settings
├── docker-compose.yml       # Development environment
├── docker-compose.prod.yml  # Production environment
├── .gitignore              # Git ignore rules
├── .pre-commit-config.yaml  # Pre-commit hooks
├── LICENSE                  # Project license
└── README.md               # Project overview
```

## Backend Structure

```
backend/
├── app/                     # Application code
│   ├── api/                # API layer
│   │   ├── v1/             # API version 1
│   │   │   ├── endpoints/  # Route handlers
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py
│   │   │   │   ├── series.py
│   │   │   │   ├── chapters.py
│   │   │   │   ├── library.py
│   │   │   │   └── watching.py
│   │   │   └── router.py   # Main API router
│   │   └── deps.py         # API dependencies
│   │
│   ├── core/               # Core configuration
│   │   ├── __init__.py
│   │   ├── config.py       # Settings management
│   │   ├── security.py     # Security utilities
│   │   ├── exceptions.py   # Custom exceptions
│   │   └── logging.py      # Logging configuration
│   │
│   ├── models/             # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── base.py         # Base model class
│   │   ├── series.py       # Series model
│   │   ├── chapter.py      # Chapter model
│   │   ├── user.py         # User model
│   │   └── watching.py     # Watch list model
│   │
│   ├── schemas/            # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── base.py         # Base schemas
│   │   ├── series.py       # Series schemas
│   │   ├── chapter.py      # Chapter schemas
│   │   ├── user.py         # User schemas
│   │   └── watching.py     # Watch list schemas
│   │
│   ├── services/           # Business logic
│   │   ├── __init__.py
│   │   ├── series.py       # Series management
│   │   ├── chapter.py      # Chapter processing
│   │   ├── library.py      # Library operations
│   │   ├── watching.py     # Watch list management
│   │   ├── mangadex.py     # MangaDex integration
│   │   └── file_processor.py # File processing
│   │
│   ├── repositories/       # Data access layer
│   │   ├── __init__.py
│   │   ├── base.py         # Base repository
│   │   ├── series.py       # Series repository
│   │   ├── chapter.py      # Chapter repository
│   │   └── watching.py     # Watch list repository
│   │
│   ├── workers/            # Background tasks
│   │   ├── __init__.py
│   │   ├── scheduler.py    # Task scheduler
│   │   ├── downloader.py   # Chapter downloader
│   │   ├── watcher.py      # Series watcher
│   │   └── processor.py    # File processor
│   │
│   ├── db/                 # Database utilities
│   │   ├── __init__.py
│   │   ├── session.py      # Database session
│   │   └── init_db.py     # Database initialization
│   │
│   └── main.py             # Application entry point
│
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   │   ├── test_services/
│   │   ├── test_repositories/
│   │   └── test_schemas/
│   ├── integration/       # Integration tests
│   │   ├── test_api/
│   │   └── test_db/
│   ├── fixtures/          # Test fixtures
│   │   ├── __init__.py
│   │   ├── series.py
│   │   └── sample_files/
│   └── conftest.py        # Pytest configuration
│
├── migrations/            # Database migrations (future)
├── scripts/              # Utility scripts
│   ├── init_db.py        # Initialize database
│   └── seed_data.py      # Seed test data
│
├── requirements.txt       # Python dependencies
├── requirements-dev.txt   # Development dependencies
├── pyproject.toml        # Python project configuration
├── .env.example          # Environment variables example
└── Dockerfile            # Backend container definition
```

## Frontend Structure

```
frontend/
├── src/
│   ├── app/                # Next.js App Router
│   │   ├── layout.tsx      # Root layout
│   │   ├── page.tsx        # Home page
│   │   ├── globals.css     # Global styles
│   │   ├── library/        # Library pages
│   │   │   ├── page.tsx    # Library listing
│   │   │   └── [id]/       # Series detail
│   │   │       └── page.tsx
│   │   ├── reader/         # Reader pages
│   │   │   └── [id]/       # Chapter reader
│   │   │       └── page.tsx
│   │   ├── watching/       # Watch list pages
│   │   │   └── page.tsx
│   │   ├── settings/       # Settings pages
│   │   │   └── page.tsx
│   │   └── api/           # API routes (if needed)
│   │       └── auth/
│   │
│   ├── components/         # React components
│   │   ├── ui/            # Base UI components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── dialog.tsx
│   │   │   └── ...
│   │   ├── layout/        # Layout components
│   │   │   ├── header.tsx
│   │   │   ├── sidebar.tsx
│   │   │   └── footer.tsx
│   │   ├── library/       # Library components
│   │   │   ├── series-grid.tsx
│   │   │   ├── series-card.tsx
│   │   │   └── series-filter.tsx
│   │   ├── reader/        # Reader components
│   │   │   ├── page-viewer.tsx
│   │   │   ├── page-controls.tsx
│   │   │   └── chapter-nav.tsx
│   │   └── common/        # Shared components
│   │       ├── loading.tsx
│   │       └── error.tsx
│   │
│   ├── lib/               # Utilities and libraries
│   │   ├── api/           # API client
│   │   │   ├── client.ts
│   │   │   ├── series.ts
│   │   │   ├── chapters.ts
│   │   │   └── watching.ts
│   │   ├── hooks/         # Custom React hooks
│   │   │   ├── use-series.ts
│   │   │   ├── use-reader.ts
│   │   │   └── use-auth.ts
│   │   ├── utils/         # Utility functions
│   │   │   ├── format.ts
│   │   │   └── validation.ts
│   │   └── constants.ts   # App constants
│   │
│   ├── stores/            # State management
│   │   ├── library.ts     # Library store
│   │   ├── reader.ts      # Reader store
│   │   ├── watching.ts    # Watch list store
│   │   └── auth.ts        # Auth store
│   │
│   ├── types/             # TypeScript types
│   │   ├── api.ts         # API types
│   │   ├── manga.ts       # Domain types
│   │   └── ui.ts          # UI types
│   │
│   └── styles/            # Additional styles
│       └── components/    # Component styles
│
├── public/                # Static assets
│   ├── images/
│   ├── fonts/
│   └── manifest.json
│
├── tests/                 # Test files
│   ├── unit/             # Unit tests
│   │   ├── components/
│   │   └── lib/
│   ├── integration/      # Integration tests
│   ├── e2e/             # E2E tests
│   │   ├── library.spec.ts
│   │   └── reader.spec.ts
│   └── setup.ts         # Test setup
│
├── package.json          # Node dependencies
├── pnpm-lock.yaml       # Lock file
├── tsconfig.json        # TypeScript config
├── next.config.js       # Next.js config
├── tailwind.config.ts   # Tailwind config
├── postcss.config.js    # PostCSS config
├── .eslintrc.js        # ESLint config
├── .prettierrc         # Prettier config
├── playwright.config.ts # Playwright config
├── vitest.config.ts    # Vitest config
├── .env.example        # Environment example
└── Dockerfile          # Frontend container
```

## Docker Structure

```
docker/
├── backend/
│   ├── Dockerfile         # Production build
│   └── Dockerfile.dev     # Development build
├── frontend/
│   ├── Dockerfile         # Production build
│   └── Dockerfile.dev     # Development build
├── nginx/
│   ├── nginx.conf         # Nginx configuration
│   └── Dockerfile         # Nginx container
└── postgres/
    └── init.sql          # Database initialization
```

## Scripts Structure

```
scripts/
├── dev/                   # Development scripts
│   ├── setup.sh          # Initial setup
│   ├── reset-db.sh       # Reset database
│   └── generate-types.sh # Generate TypeScript types
├── deploy/               # Deployment scripts
│   ├── build.sh         # Build containers
│   └── deploy.sh        # Deploy application
└── test/                # Testing scripts
    ├── run-tests.sh     # Run all tests
    └── coverage.sh      # Generate coverage
```

## Configuration Files

### Root Configuration

```
.pre-commit-config.yaml    # Pre-commit hooks
.gitignore                 # Git ignore patterns
.dockerignore             # Docker ignore patterns
docker-compose.yml        # Development environment
docker-compose.prod.yml   # Production environment
```

### Backend Configuration

```
backend/
├── pyproject.toml        # Python project config
├── requirements.txt      # Production dependencies
├── requirements-dev.txt  # Development dependencies
├── .env.example         # Environment template
└── pytest.ini           # Pytest configuration
```

### Frontend Configuration

```
frontend/
├── package.json         # Node.js dependencies
├── tsconfig.json       # TypeScript config
├── next.config.js      # Next.js config
├── tailwind.config.ts  # Tailwind CSS config
├── .eslintrc.js       # ESLint rules
├── .prettierrc        # Prettier rules
└── .env.example       # Environment template
```

## File Naming Conventions

### Backend (Python)

- **Modules**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions**: `snake_case`
- **Constants**: `SCREAMING_SNAKE_CASE`
- **Test files**: `test_*.py`

### Frontend (TypeScript/React)

- **Components**: `kebab-case.tsx` with `PascalCase` export
- **Utilities**: `kebab-case.ts`
- **Hooks**: `use-*.ts`
- **Types**: `kebab-case.ts`
- **Test files**: `*.test.ts` or `*.spec.ts`

## Module Organization Guidelines

### Backend Modules

Each feature module should contain:
- **Model**: Database schema
- **Schema**: Pydantic validation
- **Repository**: Data access
- **Service**: Business logic
- **Endpoint**: API routes

### Frontend Features

Each feature should contain:
- **Components**: UI components
- **Hooks**: Custom hooks
- **API**: API client functions
- **Store**: State management
- **Types**: TypeScript definitions

## Import Order

### Python Imports

```python
# Standard library
import os
from datetime import datetime

# Third-party libraries
from fastapi import FastAPI
from sqlalchemy import Column

# Local application
from app.core.config import settings
from app.models.series import Series
```

### TypeScript Imports

```typescript
// External libraries
import React, { useState } from 'react'
import { useRouter } from 'next/navigation'

// Internal absolute imports
import { Button } from '@/components/ui/button'
import { useLibraryStore } from '@/stores/library'

// Relative imports
import { SeriesCard } from './series-card'

// Types
import type { Series } from '@/types/manga'
```

## Environment Variables

### Backend Environment

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/kiremisu
DATABASE_POOL_SIZE=20

# Security
SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# External APIs
MANGADEX_API_URL=https://api.mangadex.org
MANGADEX_RATE_LIMIT=5

# Storage
STORAGE_PATH=/data/manga
THUMBNAIL_PATH=/data/thumbnails

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Frontend Environment

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Features
NEXT_PUBLIC_ENABLE_ANALYTICS=false
NEXT_PUBLIC_ENABLE_PWA=true

# External Services
NEXT_PUBLIC_SENTRY_DSN=
```

## Development Workflow Paths

### Adding a New Feature

1. **Backend Path**:
   ```
   models/ → schemas/ → repositories/ → services/ → endpoints/
   ```

2. **Frontend Path**:
   ```
   types/ → api/ → hooks/ → components/ → pages/
   ```

3. **Testing Path**:
   ```
   unit tests → integration tests → e2e tests
   ```

## Build Artifacts

```
# Backend build artifacts
backend/
├── dist/              # Built package
├── .coverage          # Coverage reports
└── htmlcov/          # HTML coverage

# Frontend build artifacts
frontend/
├── .next/            # Next.js build
├── out/              # Static export
└── coverage/         # Test coverage
```

## Summary

This structure provides:
- **Clear separation**: Backend, frontend, and infrastructure
- **Feature organization**: Grouped by domain
- **Scalability**: Easy to add new features
- **Testability**: Organized test structure
- **Maintainability**: Consistent patterns throughout