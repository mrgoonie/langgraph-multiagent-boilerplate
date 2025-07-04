"""
Pydantic schemas for crews, agents, and related entities
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class CrewStatusEnum(str, Enum):
    """Status options for a crew"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


# Base schemas
class CrewBase(BaseModel):
    """Base schema for crew data"""
    name: str
    description: Optional[str] = None
    status: CrewStatusEnum = CrewStatusEnum.ACTIVE
    settings: Dict[str, Any] = Field(default_factory=dict)


class AgentBase(BaseModel):
    """Base schema for agent data"""
    name: str
    description: Optional[str] = None
    system_prompt: str
    model: str
    temperature: float = 0.2
    is_supervisor: bool = False
    settings: Dict[str, Any] = Field(default_factory=dict)


class MCPServerBase(BaseModel):
    """Base schema for MCP server data"""
    name: str
    description: Optional[str] = None
    url: str
    settings: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


# Create schemas
class CrewCreate(CrewBase):
    """Schema for creating a new crew"""
    pass


class AgentCreate(AgentBase):
    """Schema for creating a new agent"""
    crew_id: UUID


class MCPServerCreate(MCPServerBase):
    """Schema for creating a new MCP server"""
    pass


# Response schemas
class CrewResponse(CrewBase):
    """Schema for crew response"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AgentResponse(AgentBase):
    """Schema for agent response"""
    id: UUID
    crew_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class MCPServerResponse(MCPServerBase):
    """Schema for MCP server response"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class MCPToolBase(BaseModel):
    """Base schema for MCP tool data"""
    name: str
    description: Optional[str] = None
    parameters_schema: Dict[str, Any] = Field(default_factory=dict)


class MCPToolResponse(MCPToolBase):
    """Schema for MCP tool response"""
    id: UUID
    mcp_server_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AgentWithTools(AgentResponse):
    """Agent schema with attached tools"""
    mcp_tools: List["MCPToolResponse"] = Field(default_factory=list)


class CrewWithAgentsAndServers(CrewResponse):
    """Crew schema with attached agents and MCP servers"""
    agents: List[AgentResponse] = Field(default_factory=list)
    mcp_servers: List[MCPServerResponse] = Field(default_factory=list)
    
    @property
    def supervisor(self) -> Optional[AgentResponse]:
        """Get the supervisor agent for this crew"""
        for agent in self.agents:
            if agent.is_supervisor:
                return agent
        return None


# Update schemas
class CrewUpdate(BaseModel):
    """Schema for updating a crew"""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CrewStatusEnum] = None
    settings: Optional[Dict[str, Any]] = None


class AgentUpdate(BaseModel):
    """Schema for updating an agent"""
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    is_supervisor: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None


class MCPServerUpdate(BaseModel):
    """Schema for updating an MCP server"""
    name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
