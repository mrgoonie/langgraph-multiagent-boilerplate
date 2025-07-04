"""
FastAPI main application entry point
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from app.core.config import settings
from app.api.routes import conversation

# Create FastAPI app with metadata for OpenAPI/Swagger docs
app = FastAPI(
    title="LangGraph Multi-Agent Boilerplate API",
    description="""
    API for the LangGraph Multi-Agent Boilerplate. 
    Build AI agent clusters with supervisor architecture, MCP tools, and more.
    """,
    version="0.1.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(conversation.router, prefix="/api")

# Add other routers here as they are implemented
# app.include_router(crews_router, prefix="/api")
# app.include_router(agents_router, prefix="/api")
# app.include_router(mcp_servers_router, prefix="/api")

# Health check endpoint
@app.get("/api/health", tags=["health"])
async def health_check():
    """Health check endpoint to verify the API is running"""
    return {"status": "ok", "version": app.version}


@app.on_event("startup")
async def startup_event():
    """Run tasks on application startup"""
    # Initialize database connections, caches, etc.
    pass


@app.on_event("shutdown")
async def shutdown_event():
    """Run tasks on application shutdown"""
    # Clean up resources
    pass


if __name__ == "__main__":
    import uvicorn
    
    # Run the application with uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
