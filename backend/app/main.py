import time
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Set
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.db.database import create_db_and_tables


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Enhanced Content Security Policy for better XSS protection
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-eval'; "  # Allow eval for Next.js dev mode
            "style-src 'self' 'unsafe-inline'; "  # Allow inline styles for Tailwind
            "img-src 'self' data: blob:; "  # Allow data URLs and blob for images
            "font-src 'self' data:; "
            "connect-src 'self' http://localhost:3000 http://localhost:3001 http://localhost:3002; "
            "media-src 'self'; "
            "object-src 'none'; "  # Prevent object/embed XSS
            "base-uri 'self'; "  # Prevent base tag injection
            "form-action 'self'; "  # Restrict form submissions
            "frame-ancestors 'none'; "  # Prevent clickjacking
            "upgrade-insecure-requests"  # Force HTTPS in production
        )
        
        # Only add HSTS in production (when using HTTPS)
        # This prevents HSTS issues in local development
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware for authentication endpoints."""
    
    def __init__(self, app):
        super().__init__(app)
        self.requests = defaultdict(list)
        
    def get_client_ip(self, request: Request) -> str:
        """Extract client IP, handling potential proxies."""
        # Check for forwarded IP headers (common in production setups)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
            
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"
    
    def is_rate_limited(self, client_ip: str, endpoint: str) -> bool:
        """Check if client has exceeded rate limit for the endpoint."""
        if not settings.RATE_LIMIT_ENABLED:
            return False
            
        current_time = time.time()
        window_start = current_time - settings.RATE_LIMIT_WINDOW_SECONDS
        
        # Clean old entries
        client_key = f"{client_ip}:{endpoint}"
        self.requests[client_key] = [
            req_time for req_time in self.requests[client_key] 
            if req_time > window_start
        ]
        
        # Check limits based on endpoint type
        if endpoint == "login":
            limit = 5  # Strict limit for login attempts
        elif endpoint in ["register", "logout"]:
            limit = 10  # Moderate limit for other auth endpoints
        else:
            return False  # No rate limiting for non-auth endpoints
            
        return len(self.requests[client_key]) >= limit
    
    def add_request(self, client_ip: str, endpoint: str):
        """Record a request for rate limiting."""
        if settings.RATE_LIMIT_ENABLED:
            client_key = f"{client_ip}:{endpoint}"
            self.requests[client_key].append(time.time())

    async def dispatch(self, request: Request, call_next):
        # Only apply rate limiting to auth endpoints
        path = request.url.path
        
        # Extract endpoint name for auth routes
        endpoint = None
        if path.startswith("/api/v1/auth/"):
            endpoint = path.split("/")[-1]  # login, register, logout, etc.
        
        if endpoint:
            client_ip = self.get_client_ip(request)
            
            # Check rate limit before processing
            if self.is_rate_limited(client_ip, endpoint):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later.",
                    headers={"Retry-After": str(settings.RATE_LIMIT_WINDOW_SECONDS)}
                )
            
            # Process request
            response = await call_next(request)
            
            # Record request only after successful processing
            # (Don't count failed requests toward rate limit to prevent lockout)
            if response.status_code < 500:  # Only count non-server-error responses
                self.add_request(client_ip, endpoint)
            
            return response
        
        # Non-auth endpoints pass through without rate limiting
        return await call_next(request)


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware using double-submit cookie pattern."""
    
    # Methods that modify state and require CSRF protection
    STATE_CHANGING_METHODS: Set[str] = {"POST", "PUT", "PATCH", "DELETE"}
    
    # Endpoints that are exempt from CSRF protection (like CSRF token generation)
    EXEMPT_PATHS: Set[str] = {
        "/api/v1/auth/csrf-token",  # Token generation endpoint
        "/docs",
        "/openapi.json",
        "/redoc",
    }
    
    def __init__(self, app):
        super().__init__(app)
    
    def is_csrf_exempt(self, path: str) -> bool:
        """Check if path is exempt from CSRF protection."""
        return any(path.startswith(exempt) for exempt in self.EXEMPT_PATHS)
    
    def extract_csrf_token_from_cookie(self, request: Request) -> str:
        """Extract CSRF token from cookie."""
        return request.cookies.get("csrf_token", "")
    
    def extract_csrf_token_from_header(self, request: Request) -> str:
        """Extract CSRF token from header."""
        return request.headers.get("X-CSRF-Token", "")
    
    async def dispatch(self, request: Request, call_next):
        # Skip CSRF protection for exempt paths and non-state-changing methods
        if (request.method not in self.STATE_CHANGING_METHODS or 
            self.is_csrf_exempt(request.url.path)):
            return await call_next(request)
        
        # Extract tokens from cookie and header
        cookie_token = self.extract_csrf_token_from_cookie(request)
        header_token = self.extract_csrf_token_from_header(request)
        
        # Validate CSRF tokens (double-submit cookie pattern)
        if not cookie_token or not header_token or cookie_token != header_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token validation failed. Please refresh the page and try again."
            )
        
        # Basic token format validation (ensure it's not empty and has reasonable length)
        if len(header_token) < 32 or len(header_token) > 128:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid CSRF token format"
            )
        
        return await call_next(request)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: Create database tables
    await create_db_and_tables()
    
    # Initialize admin user
    try:
        from app.init_admin import create_admin_user
        await create_admin_user()
    except Exception as e:
        print(f"Warning: Could not create admin user: {e}")
    
    yield
    # Shutdown: Clean up if needed
    pass

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Self-hosted manga library management system",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Add security middleware (order matters - CSRF first, then rate limiting, then headers)
app.add_middleware(CSRFProtectionMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# CORS middleware with security restrictions
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Specific methods only
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With", "X-CSRF-Token"],  # Include CSRF token header
)

# Database startup now handled by lifespan events

# Include routers
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": "KireMisu API", "version": settings.VERSION}