"""
Custom exceptions and error handling for API
"""
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, List, Union
import traceback
import logging

# Configure logging
logger = logging.getLogger(__name__)


class BaseAPIException(HTTPException):
    """Base exception class for all API exceptions"""
    def __init__(
        self, 
        status_code: int, 
        detail: str,
        headers: Optional[Dict[str, str]] = None,
        error_code: Optional[str] = None,
        errors: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code or f"ERROR_{status_code}"
        self.errors = errors or []


class NotFoundError(BaseAPIException):
    """Resource not found exception"""
    def __init__(
        self,
        detail: str = "Resource not found",
        error_code: str = "NOT_FOUND",
        headers: Optional[Dict[str, str]] = None,
        errors: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            headers=headers,
            error_code=error_code,
            errors=errors
        )


class BadRequestError(BaseAPIException):
    """Bad request exception"""
    def __init__(
        self,
        detail: str = "Invalid request data",
        error_code: str = "BAD_REQUEST",
        headers: Optional[Dict[str, str]] = None,
        errors: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            headers=headers,
            error_code=error_code,
            errors=errors
        )


class UnauthorizedError(BaseAPIException):
    """Unauthorized access exception"""
    def __init__(
        self,
        detail: str = "Authentication required",
        error_code: str = "UNAUTHORIZED",
        headers: Optional[Dict[str, str]] = None,
        errors: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers=headers,
            error_code=error_code,
            errors=errors
        )


class ForbiddenError(BaseAPIException):
    """Forbidden access exception"""
    def __init__(
        self,
        detail: str = "Access forbidden",
        error_code: str = "FORBIDDEN",
        headers: Optional[Dict[str, str]] = None,
        errors: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            headers=headers,
            error_code=error_code,
            errors=errors
        )


class ConflictError(BaseAPIException):
    """Resource conflict exception"""
    def __init__(
        self,
        detail: str = "Resource conflict",
        error_code: str = "CONFLICT",
        headers: Optional[Dict[str, str]] = None,
        errors: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            headers=headers,
            error_code=error_code,
            errors=errors
        )


class ServerError(BaseAPIException):
    """Internal server error exception"""
    def __init__(
        self,
        detail: str = "Internal server error",
        error_code: str = "SERVER_ERROR",
        headers: Optional[Dict[str, str]] = None,
        errors: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            headers=headers,
            error_code=error_code,
            errors=errors
        )


async def api_exception_handler(request: Request, exc: BaseAPIException) -> JSONResponse:
    """Handler for BaseAPIException and its subclasses"""
    # Log the error
    logger.error(
        f"API Error: {exc.status_code} {exc.error_code} - {exc.detail}",
        extra={"request_path": request.url.path}
    )
    
    # Include error details in response
    content = {
        "status_code": exc.status_code,
        "error_code": exc.error_code,
        "detail": exc.detail,
    }
    
    if exc.errors:
        content["errors"] = exc.errors
    
    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        headers=exc.headers
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handler for FastAPI's HTTPException"""
    # Log the error
    logger.error(
        f"HTTP Exception: {exc.status_code} - {exc.detail}",
        extra={"request_path": request.url.path}
    )
    
    # Convert to our format
    content = {
        "status_code": exc.status_code,
        "error_code": f"ERROR_{exc.status_code}",
        "detail": exc.detail,
    }
    
    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        headers=exc.headers,
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler for validation errors"""
    # Log the error
    logger.error(
        f"Validation Error: {str(exc)}",
        extra={"request_path": request.url.path}
    )
    
    # Process validation errors
    errors = []
    if hasattr(exc, "errors"):
        for error in exc.errors():
            errors.append({
                "loc": error.get("loc", []),
                "msg": error.get("msg", ""),
                "type": error.get("type", "")
            })
    
    content = {
        "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "error_code": "VALIDATION_ERROR",
        "detail": "Validation error in request data",
        "errors": errors
    }
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=content,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler for unhandled exceptions"""
    # Log the full error with traceback in development
    error_detail = f"{type(exc).__name__}: {str(exc)}"
    logger.error(
        f"Unhandled Exception: {error_detail}",
        extra={
            "request_path": request.url.path,
            "traceback": traceback.format_exc()
        }
    )
    
    # In production, don't leak implementation details
    content = {
        "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "error_code": "SERVER_ERROR",
        "detail": "An unexpected error occurred"
    }
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=content,
    )
