# KireMisu Development Standards

This document defines coding standards, conventions, and best practices for the KireMisu project.

## Code Style Guidelines

### Python Code Style

#### Ruff Configuration

```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "UP",  # pyupgrade
    "N",   # pep8-naming
    "S",   # flake8-bandit (security)
    "C90", # mccabe complexity
    "ANN", # flake8-annotations
    "ASYNC", # flake8-async
]
ignore = [
    "ANN101",  # Missing type annotation for self
    "ANN102",  # Missing type annotation for cls
]

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["S101"]  # Allow assert in tests

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

#### Python Style Examples

```python
# Good: Clear imports, type hints, docstrings
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.series import Series
from app.schemas.series import SeriesCreate


async def create_series(
    db: AsyncSession,
    series_data: SeriesCreate,
    user_id: UUID,
) -> Series:
    """Create a new series in the database.
    
    Args:
        db: Database session
        series_data: Series creation data
        user_id: ID of the user creating the series
        
    Returns:
        Created series instance
        
    Raises:
        HTTPException: If series with same title exists
    """
    # Check for duplicates
    existing = await db.execute(
        select(Series).where(Series.title == series_data.title)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Series with this title already exists",
        )
    
    # Create new series
    series = Series(
        **series_data.model_dump(),
        user_id=user_id,
        created_at=datetime.utcnow(),
    )
    
    db.add(series)
    await db.commit()
    await db.refresh(series)
    
    return series
```

### TypeScript/JavaScript Code Style

#### ESLint & Prettier Configuration

```javascript
// .eslintrc.js
module.exports = {
  extends: [
    'next/core-web-vitals',
    'plugin:@typescript-eslint/recommended',
    'plugin:react-hooks/recommended',
    'prettier'
  ],
  parser: '@typescript-eslint/parser',
  plugins: ['@typescript-eslint'],
  rules: {
    '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    '@typescript-eslint/explicit-function-return-type': 'off',
    '@typescript-eslint/no-explicit-any': 'error',
    'react-hooks/rules-of-hooks': 'error',
    'react-hooks/exhaustive-deps': 'warn',
    'no-console': ['warn', { allow: ['warn', 'error'] }]
  }
}

// .prettierrc
{
  "semi": false,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 2,
  "useTabs": false
}
```

#### TypeScript Style Examples

```typescript
// Good: Clear types, consistent formatting, proper exports
import { FC, useState, useCallback } from 'react'
import { Series, Chapter } from '@/types/manga'
import { useLibraryStore } from '@/stores/library'

interface SeriesViewerProps {
  series: Series
  initialChapter?: Chapter
  onChapterChange?: (chapter: Chapter) => void
}

export const SeriesViewer: FC<SeriesViewerProps> = ({
  series,
  initialChapter,
  onChapterChange,
}) => {
  const [currentChapter, setCurrentChapter] = useState<Chapter | undefined>(initialChapter)
  const { updateReadingProgress } = useLibraryStore()

  const handleChapterSelect = useCallback(
    (chapter: Chapter) => {
      setCurrentChapter(chapter)
      onChapterChange?.(chapter)
      
      // Update reading progress
      updateReadingProgress(series.id, chapter.id)
    },
    [series.id, onChapterChange, updateReadingProgress]
  )

  return (
    <div className="flex h-full">
      <ChapterList 
        chapters={series.chapters}
        currentChapter={currentChapter}
        onSelect={handleChapterSelect}
      />
      {currentChapter && (
        <ChapterReader chapter={currentChapter} />
      )}
    </div>
  )
}
```

## Naming Conventions

### File Naming

| Type | Convention | Example |
|------|------------|---------|
| Python files | snake_case | `series_service.py` |
| TypeScript files | kebab-case | `series-viewer.tsx` |
| React components | PascalCase | `SeriesCard.tsx` |
| Test files | test_ prefix or .test suffix | `test_series.py`, `SeriesCard.test.tsx` |
| Config files | kebab-case | `docker-compose.yml` |

### Variable and Function Naming

```python
# Python
class SeriesRepository:  # PascalCase for classes
    MAX_RESULTS = 100  # SCREAMING_SNAKE_CASE for constants
    
    def find_by_genre(self, genre: str):  # snake_case for methods
        series_list = []  # snake_case for variables
        ...

# TypeScript
const MAX_RESULTS = 100  // SCREAMING_SNAKE_CASE for constants

interface SeriesData {  // PascalCase for types/interfaces
  seriesTitle: string  // camelCase for properties
  chapterCount: number
}

function findSeriesByGenre(genre: string): Series[] {  // camelCase for functions
  const seriesList: Series[] = []  // camelCase for variables
  ...
}
```

### API Endpoint Naming

```
# RESTful resource naming
GET    /api/v1/series              # Plural for collections
GET    /api/v1/series/{id}         # Singular resource
GET    /api/v1/series/{id}/chapters # Nested resources
POST   /api/v1/series/{id}/watch   # Actions as sub-resources
DELETE /api/v1/watched-series/{id} # Kebab-case for compound words
```

## Git Commit Standards

### Conventional Commits Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Commit Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, missing semicolons, etc.)
- **refactor**: Code refactoring
- **perf**: Performance improvements
- **test**: Adding or updating tests
- **build**: Build system or dependency changes
- **ci**: CI/CD configuration changes
- **chore**: Other changes that don't modify src or test files

### Examples

```bash
# Good commit messages
feat(library): add series filtering by genre
fix(reader): resolve page navigation in vertical mode
docs(api): update series endpoint documentation
refactor(db): extract repository base class
test(series): add integration tests for series creation

# Bad commit messages
updated stuff
fix bug
WIP
changes
```

## Pull Request Standards

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] E2E tests pass (if applicable)
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No console.log or debug code
- [ ] Lint and format checks pass
```

### PR Requirements

1. **Title**: Use conventional commit format
2. **Description**: Clear explanation of what and why
3. **Tests**: All tests must pass
4. **Review**: At least one approval (when team grows)
5. **Size**: Keep PRs small and focused (<500 lines preferred)

## Error Handling Standards

### Backend Error Handling

```python
# Define custom exceptions
class BusinessError(Exception):
    """Base class for business logic errors."""
    pass

class ResourceNotFoundError(BusinessError):
    """Raised when a requested resource doesn't exist."""
    pass

class ValidationError(BusinessError):
    """Raised when input validation fails."""
    pass

# Use structured error responses
from fastapi import HTTPException

async def get_series(series_id: UUID):
    try:
        series = await series_service.get(series_id)
        if not series:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "resource_not_found",
                    "message": f"Series {series_id} not found",
                    "resource": "series",
                    "id": str(series_id)
                }
            )
        return series
    except ValidationError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "validation_error",
                "message": str(e),
                "fields": e.fields if hasattr(e, 'fields') else None
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_server_error",
                "message": "An unexpected error occurred"
            }
        )
```

### Frontend Error Handling

```typescript
// Define error types
interface ApiError {
  error: string
  message: string
  details?: Record<string, unknown>
}

// Global error handler
export async function handleApiError(error: unknown): Promise<void> {
  if (axios.isAxiosError(error)) {
    const apiError = error.response?.data as ApiError
    
    switch (error.response?.status) {
      case 401:
        // Redirect to login
        window.location.href = '/login'
        break
      case 404:
        toast.error(apiError.message || 'Resource not found')
        break
      case 422:
        toast.error(apiError.message || 'Validation failed')
        break
      default:
        toast.error('An unexpected error occurred')
    }
  } else {
    console.error('Unexpected error:', error)
    toast.error('An unexpected error occurred')
  }
}

// Component error boundary
export class ErrorBoundary extends Component<Props, State> {
  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Component error:', error, errorInfo)
    // Log to error reporting service
  }
  
  render() {
    if (this.state.hasError) {
      return <ErrorFallback />
    }
    return this.props.children
  }
}
```

## Testing Standards

### Test Organization

```
backend/tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── fixtures/       # Test data
└── conftest.py     # Shared fixtures

frontend/tests/
├── unit/           # Component tests
├── integration/    # API integration tests
├── e2e/           # End-to-end tests
└── setup.ts       # Test configuration
```

### Test Naming

```python
# Python test naming
def test_should_create_series_when_valid_data():
    """Test that series creation succeeds with valid input."""
    ...

def test_should_raise_error_when_duplicate_title():
    """Test that duplicate title raises conflict error."""
    ...
```

```typescript
// TypeScript test naming
describe('SeriesCard', () => {
  it('should display series title', () => {
    // test implementation
  })
  
  it('should call onSelect when clicked', () => {
    // test implementation
  })
})
```

### Test Coverage Requirements

- **Unit Tests**: Minimum 80% coverage
- **Critical Paths**: 100% E2E coverage
- **New Code**: All new code must include tests
- **Bug Fixes**: Must include regression test

## Documentation Standards

### Code Documentation

```python
# Python docstrings (Google style)
def process_chapter(
    file_path: str,
    options: ProcessOptions | None = None
) -> ChapterData:
    """Process a manga chapter file.
    
    Extract images and metadata from various manga file formats.
    
    Args:
        file_path: Path to the chapter file
        options: Optional processing configuration
        
    Returns:
        Processed chapter data including images and metadata
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ProcessingError: If file format is unsupported
        
    Example:
        >>> data = process_chapter("/manga/chapter1.cbz")
        >>> print(f"Pages: {len(data.pages)}")
    """
    ...
```

```typescript
/**
 * Process a manga chapter file
 * 
 * @param filePath - Path to the chapter file
 * @param options - Optional processing configuration
 * @returns Processed chapter data
 * @throws {ProcessingError} If file format is unsupported
 * 
 * @example
 * ```ts
 * const data = await processChapter('/manga/chapter1.cbz')
 * console.log(`Pages: ${data.pages.length}`)
 * ```
 */
export async function processChapter(
  filePath: string,
  options?: ProcessOptions
): Promise<ChapterData> {
  ...
}
```

### API Documentation

All endpoints must include OpenAPI documentation:

```python
@router.post(
    "/series",
    response_model=SeriesResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new series",
    description="Create a new manga series in the library",
    responses={
        201: {"description": "Series created successfully"},
        409: {"description": "Series with this title already exists"},
        422: {"description": "Invalid input data"}
    }
)
async def create_series(
    series: SeriesCreate,
    db: AsyncSession = Depends(get_db)
) -> SeriesResponse:
    """Create a new series in the library."""
    ...
```

## Security Standards

### Input Validation

- Always validate input at the API boundary
- Use Pydantic for Python, Zod for TypeScript
- Sanitize user-generated content
- Validate file uploads (type, size, content)

### Authentication & Authorization

- Use JWT tokens with appropriate expiration
- Store sensitive data in environment variables
- Never log sensitive information
- Implement rate limiting on public endpoints

### Dependencies

- Regular dependency updates (monthly)
- Security audit with `pip-audit` and `npm audit`
- Pin major versions in production
- Document any security exceptions

## Performance Standards

### Backend Performance

- API response time < 200ms for simple queries
- Database queries must use appropriate indexes
- Pagination for list endpoints (default 50, max 100)
- Connection pooling for database and HTTP clients

### Frontend Performance

- Initial page load < 3 seconds
- Lazy load images and components
- Implement virtual scrolling for large lists
- Use React.memo and useMemo appropriately

## Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: ruff-format
        name: Format Python code
        entry: ruff format
        language: system
        types: [python]
      
      - id: ruff-lint
        name: Lint Python code
        entry: ruff check --fix
        language: system
        types: [python]
      
      - id: prettier
        name: Format JS/TS code
        entry: pnpm prettier --write
        language: system
        files: \.(js|jsx|ts|tsx|json|md)$
      
      - id: eslint
        name: Lint JS/TS code
        entry: pnpm eslint --fix
        language: system
        files: \.(js|jsx|ts|tsx)$
      
      - id: type-check
        name: TypeScript type check
        entry: pnpm tsc --noEmit
        language: system
        pass_filenames: false
```

## Summary

These standards ensure:
- **Consistency**: Uniform code style across the project
- **Quality**: Automated checks catch issues early
- **Maintainability**: Clear patterns and documentation
- **Security**: Best practices for secure coding
- **Performance**: Guidelines for optimal performance