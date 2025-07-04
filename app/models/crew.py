"""
Database models for AI crews and related entities
"""
import enum
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON, Enum, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, relationship, mapped_column

from app.db.base import Base


# Import the metadata from SQLAlchemy
from sqlalchemy import MetaData

# Create a metadata object with the same schema as Base
metadata = MetaData(schema='public')

# Association table for crews and MCP servers
crew_mcp_association = Table(
    "crew_mcp_servers",
    metadata,
    Column("crew_id", UUID(as_uuid=True), ForeignKey("crews.id", ondelete="CASCADE"), primary_key=True),
    Column("mcp_server_id", UUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), primary_key=True)
)


class CrewStatus(enum.Enum):
    """Status of an AI crew"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


class Crew(Base):
    """AI Crew model - a group of AI agents working together"""
    __tablename__ = "crews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=Base.generate_uuid
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[CrewStatus] = mapped_column(
        Enum(CrewStatus), default=CrewStatus.ACTIVE, nullable=False
    )
    settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # Relationships
    agents: Mapped[List["Agent"]] = relationship(
        "Agent", back_populates="crew", cascade="all, delete-orphan"
    )
    
    # Many-to-many relationship with MCP servers
    mcp_servers = relationship(
        "MCPServer",
        secondary=crew_mcp_association,
        back_populates="crews"
    )
    
    # Conversations
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation", back_populates="crew", cascade="all, delete-orphan"
    )

    @property
    def supervisor_agent(self) -> Optional["Agent"]:
        """Get the supervisor agent for this crew"""
        for agent in self.agents:
            if agent.is_supervisor:
                return agent
        return None


class Agent(Base):
    """AI Agent model - an individual AI agent within a crew"""
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=Base.generate_uuid
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    temperature: Mapped[float] = mapped_column(default=0.2, nullable=False)
    is_supervisor: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Foreign keys
    crew_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crews.id", ondelete="CASCADE"), nullable=False
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # Relationships
    crew: Mapped["Crew"] = relationship("Crew", back_populates="agents")
    
    # Agent-specific tools and capabilities would go here
    mcp_tools: Mapped[List["AgentTool"]] = relationship(
        "AgentTool", back_populates="agent", cascade="all, delete-orphan"
    )
    
    # Activity logs
    activity_logs: Mapped[List["ActivityLog"]] = relationship(
        "ActivityLog", back_populates="agent", cascade="all, delete-orphan"
    )


class MCPServer(Base):
    """MCP Server model - provides tools via MCP protocol"""
    __tablename__ = "mcp_servers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=Base.generate_uuid
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships - many-to-many with crews
    crews = relationship(
        "Crew",
        secondary=crew_mcp_association,
        back_populates="mcp_servers"
    )
    
    # Available tools in this MCP server
    tools: Mapped[List["MCPTool"]] = relationship(
        "MCPTool", back_populates="mcp_server", cascade="all, delete-orphan"
    )


class MCPTool(Base):
    """Model for tools available in an MCP server"""
    __tablename__ = "mcp_tools"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=Base.generate_uuid
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    parameters_schema: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    # Foreign keys
    mcp_server_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # Relationships
    mcp_server: Mapped["MCPServer"] = relationship("MCPServer", back_populates="tools")
    agent_tools: Mapped[List["AgentTool"]] = relationship(
        "AgentTool", back_populates="mcp_tool", cascade="all, delete-orphan"
    )


class AgentTool(Base):
    """Association model for agents and their enabled MCP tools"""
    __tablename__ = "agent_tools"

    # Composite primary key
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True
    )
    mcp_tool_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mcp_tools.id", ondelete="CASCADE"), primary_key=True
    )
    
    # Tool-specific settings
    settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", back_populates="mcp_tools")
    mcp_tool: Mapped["MCPTool"] = relationship("MCPTool", back_populates="agent_tools")
