import time
from collections import defaultdict
from contextlib import asynccontextmanager
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
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self' http://localhost:3000 http://localhost:3001 http://localhost:3002; "
            "frame-ancestors 'none'"
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

# Add security middleware (order matters - rate limiting first, then headers)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# CORS middleware with security restrictions
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Specific methods only
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],  # Specific headers only
)

# Database startup now handled by lifespan events

# Include routers
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": "KireMisu API", "version": settings.VERSION}