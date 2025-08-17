# Security Development Checklist

## Pre-Commit Security Checklist ✓

Before every commit, verify:

- [ ] **No hardcoded credentials** - No passwords, API keys, tokens in code
- [ ] **Authentication required** - All user data endpoints require JWT
- [ ] **Input validation** - All user inputs validated and sanitized
- [ ] **User-scoped access** - No cross-user data access possible
- [ ] **Security tests pass** - Tests cover security scenarios
- [ ] **Environment variables** - All config uses env vars, not hardcoded
- [ ] **Error messages safe** - No sensitive info leaked in errors
- [ ] **File path validation** - Directory traversal prevention
- [ ] **HTTPS enforced** - Production configs require HTTPS
- [ ] **Docker tested** - Security works in containerized environment

## Security Testing Commands
```bash
# Run security-focused tests
cd backend && uv run pytest tests/security/ -v

# Check for hardcoded secrets (if git-secrets installed)
git secrets --scan

# Dependency vulnerability scan
cd backend && uv run safety check

# Docker security scan
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image kiremisu:latest
```

## Critical Security Patterns

### Authentication Required
```python
# ✅ REQUIRED: JWT for all user endpoints
@router.get("/api/series/{series_id}")
async def get_series(
    series_id: UUID,
    current_user: User = Depends(get_current_user)  # Always required
):
    return await series_service.get_user_series(series_id, current_user.id)
```

### Input Validation
```python
# ✅ REQUIRED: Pydantic models for all inputs
class SeriesCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    
    @validator('title')
    def sanitize_title(cls, v):
        return html.escape(v.strip())
```

### File Path Security
```python
# ✅ REQUIRED: Path validation to prevent directory traversal
def validate_file_path(base_path: str, file_path: str) -> str:
    base = Path(base_path).resolve()
    target = (base / file_path).resolve()
    
    if not target.is_relative_to(base):
        raise ValueError("Invalid file path: directory traversal detected")
    
    return str(target)
```

For detailed security implementation patterns, see the full SECURITY.md documentation.
