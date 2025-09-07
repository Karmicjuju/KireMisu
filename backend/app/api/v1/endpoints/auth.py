from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.services.user import UserService
from app.schemas.user import Token, TokenData, UserResponse, UserCreate

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Dependency to get UserService instance."""
    return UserService(db)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    request: Request,
    user_service: UserService = Depends(get_user_service)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Get token from cookie first, then try Authorization header
    token = request.cookies.get("auth-token")
    if not token:
        authorization: str = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]
    
    if not token:
        raise credentials_exception
        
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = user_service.get_user_by_username(token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """Register a new user (limited to single user initially)."""
    
    # Check if username already exists
    if user_service.user_repo.is_username_taken(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Check if email already exists
    if user_service.user_repo.is_email_taken(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
    
    # Check if any users already exist (single user limit)
    if user_service.user_repo.get_active_users_count() > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is currently limited to a single user"
        )
    
    try:
        # Create the user (password validation happens in the schema)
        user = user_service.create_user(user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User registration failed"
        )

@router.post("/login", response_model=Token)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(get_user_service)
):
    user = user_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # Set httpOnly cookie for authentication with environment-based security
    response.set_cookie(
        key="auth-token",
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # 30 minutes in seconds
        httponly=True,
        secure=settings.ENVIRONMENT == "production",  # Secure cookies in production
        samesite="lax"
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
async def logout(response: Response):
    """Logout endpoint - clears the auth cookie."""
    response.delete_cookie(
        key="auth-token", 
        secure=settings.ENVIRONMENT == "production",  # Match security setting
        samesite="lax"
    )
    return {"message": "Successfully logged out"}

@router.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user = Depends(get_current_active_user)):
    return current_user