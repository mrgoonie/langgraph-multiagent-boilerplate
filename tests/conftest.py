"""
Test configuration and fixtures
"""
import asyncio
import pytest
import uuid
import os
from typing import AsyncGenerator, Dict
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from dotenv import load_dotenv

# Load test environment variables
load_dotenv(".env.test", override=True)

from app.db.base import Base, get_db
from app.main import app
from app.core.config import settings
from app.models.crew import Crew, Agent, MCPServer, MCPTool
from app.models.conversation import Conversation, Message, MessageRole, MessageStatus


# Use in-memory SQLite for local tests, PostgreSQL for CI
# Check if we're running in CI by looking for DATABASE_URL environment variable
TEST_DATABASE_URL = os.environ.get("DATABASE_URL") or "sqlite+aiosqlite:///:memory:"
print(f"Using database URL for tests: {TEST_DATABASE_URL}")


# Create a test engine and session factory
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# Override get_db with test session
async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get a test database session"""
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest.fixture
async def setup_test_db():
    """Set up a test database with tables"""
    # For SQLite in-memory, create tables and drop them after tests
    if 'sqlite' in TEST_DATABASE_URL:
        # Create all tables
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        yield
        
        # Drop all tables
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    else:
        # For PostgreSQL in CI, tables are created by the GitHub workflow script
        # We'll truncate tables after tests to keep the DB clean
        yield
        
        # Clean up data but keep tables
        try:
            async with test_engine.begin() as conn:
                # Get all table names
                tables = Base.metadata.tables.keys()
                for table in tables:
                    # Use truncate instead of drop
                    await conn.execute(f"TRUNCATE TABLE {table} CASCADE")
        except Exception as e:
            print(f"Error cleaning up tables: {e}")
            # Continue without failing tests


@pytest.fixture
async def db_session(setup_test_db) -> AsyncGenerator[AsyncSession, None]:
    """Yield a test database session"""
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest.fixture
def test_client(db_session) -> TestClient:
    """Create a test client with test database session"""
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as client:
        yield client


@pytest.fixture
def event_loop():
    """Create an event loop for async tests"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_crew(db_session) -> Crew:
    """Create a test crew in the database"""
    crew = Crew(
        name="Test Crew",
        description="A crew for testing",
        metadata={"test": True}
    )
    db_session.add(crew)
    await db_session.commit()
    await db_session.refresh(crew)
    return crew


@pytest.fixture
async def test_mcp_server(db_session) -> MCPServer:
    """Create a test MCP server in the database"""
    mcp_server = MCPServer(
        name="Test MCP Server",
        url="http://test-mcp-server.example.com",
        description="A MCP server for testing",
        metadata={"test": True}
    )
    db_session.add(mcp_server)
    await db_session.commit()
    await db_session.refresh(mcp_server)
    return mcp_server


@pytest.fixture
async def test_mcp_tool(db_session, test_mcp_server) -> MCPTool:
    """Create a test MCP tool in the database"""
    tool = MCPTool(
        server_id=test_mcp_server.id,
        name="test-tool",
        description="A tool for testing",
        parameters={"param1": "string", "param2": "number"},
        metadata={"test": True}
    )
    db_session.add(tool)
    await db_session.commit()
    await db_session.refresh(tool)
    return tool


@pytest.fixture
async def test_agent(db_session, test_crew) -> Agent:
    """Create a test agent in the database"""
    agent = Agent(
        crew_id=test_crew.id,
        name="Test Agent",
        description="An agent for testing",
        system_prompt="You are a test agent",
        model="test-model",
        is_supervisor=True,
        metadata={"test": True}
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)
    return agent


@pytest.fixture
async def test_conversation(db_session, test_crew) -> Conversation:
    """Create a test conversation in the database"""
    conversation = Conversation(
        user_id="test-user",
        crew_id=test_crew.id,
        title="Test Conversation",
        metadata={"test": True}
    )
    db_session.add(conversation)
    await db_session.commit()
    await db_session.refresh(conversation)
    return conversation


@pytest.fixture
async def test_message(db_session, test_conversation, test_agent) -> Message:
    """Create a test message in the database"""
    message = Message(
        conversation_id=test_conversation.id,
        role=MessageRole.AGENT,
        content="This is a test message",
        agent_id=test_agent.id,
        status=MessageStatus.COMPLETED,
        metadata={"test": True}
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)
    return message


@pytest.fixture
def auth_headers() -> Dict[str, str]:
    """Generate test authentication headers"""
    from jose import jwt
    
    # Create a test token
    token_payload = {
        "sub": "test-user",
        "exp": 9999999999  # Far future expiration
    }
    token = jwt.encode(
        token_payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    
    return {"Authorization": f"Bearer {token}"}
