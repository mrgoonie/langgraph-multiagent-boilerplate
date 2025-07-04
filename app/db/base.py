"""
Database setup and configuration
"""
import uuid
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings

# Create the SQLAlchemy async engine for the configured database URL
engine = create_async_engine(
    str(settings.database_url).replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.debug,
    pool_pre_ping=True,
)

# Session factories
async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models"""
    
    # Use a specific schema if configured
    # Note: We're using __table_args__ instead of directly setting metadata
    # because 'metadata' is a reserved attribute in SQLAlchemy Declarative API
    __table_args__ = {'schema': settings.database_schema}
    
    @classmethod
    def generate_uuid(cls) -> uuid.UUID:
        """Generate a UUID for a model"""
        return uuid.uuid4()


# Dependency to get the DB session
async def get_db():
    """Dependency for FastAPI to get a database session"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
