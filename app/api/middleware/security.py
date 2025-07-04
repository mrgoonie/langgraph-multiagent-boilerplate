"""
Security middleware for API authentication and protection
"""
from fastapi import Request, Response, HTTPException, status
import time
from jose import jwt, JWTError
from typing import Optional, Callable, Dict, Any, Awaitable
import logging

from app.core.config import settings
from app.api.exceptions import UnauthorizedError, ForbiddenError

# Configure logging
logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter implementation"""
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.request_log: Dict[str, list] = {}  # key: IP, value: list of timestamps
    
    def check_rate_limit(self, client_ip: str) -> bool:
        """
        Check if a client has exceeded their rate limit
        
        Args:
            client_ip: The client's IP address
            
        Returns:
            True if allowed, False if rate limited
        """
        current_time = time.time()
        minute_ago = current_time - 60
        
        # Initialize request log for this IP if not exists
        if client_ip not in self.request_log:
            self.request_log[client_ip] = []
        
        # Filter out old requests
        self.request_log[client_ip] = [t for t in self.request_log[client_ip] if t > minute_ago]
        
        # Check if rate limit exceeded
        if len(self.request_log[client_ip]) >= self.requests_per_minute:
            return False
        
        # Log this request
        self.request_log[client_ip].append(current_time)
        return True
    
    async def __call__(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Rate limiter middleware implementation"""
        # Skip rate limiting for local development if needed
        if settings.debug and request.client.host in ("127.0.0.1", "localhost"):
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host
        
        # Check rate limit
        if not self.check_rate_limit(client_ip):
            logger.warning(f"Rate limit exceeded for IP {client_ip}")
            return Response(
                content={"detail": "Rate limit exceeded. Please try again later."},
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json"
            )
        
        # Continue processing the request
        return await call_next(request)


async def get_current_user_from_token(token: str) -> dict:
    """
    Decode JWT token and return user information
    
    Args:
        token: The JWT token to decode
        
    Returns:
        User information from the token
        
    Raises:
        UnauthorizedError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token, 
            settings.jwt_secret_key, 
            algorithms=[settings.jwt_algorithm]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise UnauthorizedError("Invalid authentication token")
        
        # You could fetch more user details from the database here
        return {"user_id": user_id}
        
    except JWTError:
        raise UnauthorizedError("Invalid authentication token")


async def auth_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Authentication middleware"""
    # Skip auth for public endpoints
    public_paths = [
        "/api/docs", 
        "/api/redoc", 
        "/api/openapi.json",
        "/api/health",
        # Add other public endpoints as needed
    ]
    
    for path in public_paths:
        if request.url.path.startswith(path):
            return await call_next(request)
    
    # Extract token from header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise UnauthorizedError("Authentication required")
    
    token = auth_header.replace("Bearer ", "")
    
    # Validate token and get user
    try:
        user = await get_current_user_from_token(token)
        # Add user info to request state
        request.state.user = user
        return await call_next(request)
    except UnauthorizedError as e:
        return Response(
            content={"detail": str(e)},
            status_code=status.HTTP_401_UNAUTHORIZED,
            media_type="application/json"
        )


class SecurityHeadersMiddleware:
    """Add security headers to responses"""
    async def __call__(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response
