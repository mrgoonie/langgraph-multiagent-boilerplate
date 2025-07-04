"""
Service for managing crews and agents
"""
from typing import Dict, List, Optional, Any
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crew import Crew, Agent, MCPServer, MCPTool, AgentTool, crew_mcp_association
from app.schemas.crew import CrewCreate, CrewUpdate, AgentCreate, AgentUpdate


class CrewService:
    """Service for crew-related operations"""
    
    @staticmethod
    async def get_crews(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Crew]:
        """Get all crews with pagination"""
        query = select(Crew).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_crew(db: AsyncSession, crew_id: uuid.UUID) -> Optional[Crew]:
        """Get a crew by ID"""
        query = select(Crew).where(Crew.id == crew_id)
        result = await db.execute(query)
        return result.scalars().first()
    
    @staticmethod
    async def create_crew(db: AsyncSession, crew_data: CrewCreate) -> Crew:
        """Create a new crew"""
        crew = Crew(**crew_data.model_dump())
        db.add(crew)
        await db.flush()
        return crew
    
    @staticmethod
    async def update_crew(
        db: AsyncSession, crew_id: uuid.UUID, crew_data: CrewUpdate
    ) -> Optional[Crew]:
        """Update a crew"""
        # Get the existing crew
        crew = await CrewService.get_crew(db, crew_id)
        if not crew:
            return None
        
        # Update attributes
        update_data = crew_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(crew, key, value)
        
        await db.flush()
        return crew
    
    @staticmethod
    async def delete_crew(db: AsyncSession, crew_id: uuid.UUID) -> bool:
        """Delete a crew"""
        crew = await CrewService.get_crew(db, crew_id)
        if not crew:
            return False
        
        await db.delete(crew)
        await db.flush()
        return True
    
    @staticmethod
    async def add_mcp_server_to_crew(
        db: AsyncSession, crew_id: uuid.UUID, server_id: uuid.UUID
    ) -> bool:
        """Add an MCP server to a crew"""
        # Check if crew and server exist
        crew = await CrewService.get_crew(db, crew_id)
        server = await MCPServerService.get_server(db, server_id)
        
        if not crew or not server:
            return False
        
        # Add server to crew's MCP servers
        crew.mcp_servers.append(server)
        await db.flush()
        return True
    
    @staticmethod
    async def remove_mcp_server_from_crew(
        db: AsyncSession, crew_id: uuid.UUID, server_id: uuid.UUID
    ) -> bool:
        """Remove an MCP server from a crew"""
        # Check if crew and server exist
        crew = await CrewService.get_crew(db, crew_id)
        server = await MCPServerService.get_server(db, server_id)
        
        if not crew or not server:
            return False
        
        # Remove server from crew's MCP servers
        if server in crew.mcp_servers:
            crew.mcp_servers.remove(server)
            await db.flush()
            return True
        return False


class AgentService:
    """Service for agent-related operations"""
    
    @staticmethod
    async def get_agents(db: AsyncSession, crew_id: Optional[uuid.UUID] = None) -> List[Agent]:
        """Get all agents, optionally filtered by crew"""
        if crew_id:
            query = select(Agent).where(Agent.crew_id == crew_id)
        else:
            query = select(Agent)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_agent(db: AsyncSession, agent_id: uuid.UUID) -> Optional[Agent]:
        """Get an agent by ID"""
        query = select(Agent).where(Agent.id == agent_id)
        result = await db.execute(query)
        return result.scalars().first()
    
    @staticmethod
    async def create_agent(db: AsyncSession, agent_data: AgentCreate) -> Agent:
        """Create a new agent"""
        # Check if this is set as a supervisor
        if agent_data.is_supervisor:
            # If this agent is a supervisor, ensure no other agent in the crew is a supervisor
            crew_id = agent_data.crew_id
            query = select(Agent).where(
                (Agent.crew_id == crew_id) & (Agent.is_supervisor == True)
            )
            result = await db.execute(query)
            existing_supervisor = result.scalars().first()
            
            if existing_supervisor:
                # Remove supervisor status from the existing supervisor
                existing_supervisor.is_supervisor = False
                await db.flush()
        
        # Create the new agent
        agent = Agent(**agent_data.model_dump())
        db.add(agent)
        await db.flush()
        return agent
    
    @staticmethod
    async def update_agent(
        db: AsyncSession, agent_id: uuid.UUID, agent_data: AgentUpdate
    ) -> Optional[Agent]:
        """Update an agent"""
        # Get the existing agent
        agent = await AgentService.get_agent(db, agent_id)
        if not agent:
            return None
        
        # Check if we're updating supervisor status
        if agent_data.is_supervisor is not None and agent_data.is_supervisor and not agent.is_supervisor:
            # If making this agent a supervisor, ensure no other agent in the crew is a supervisor
            query = select(Agent).where(
                (Agent.crew_id == agent.crew_id) & 
                (Agent.id != agent_id) & 
                (Agent.is_supervisor == True)
            )
            result = await db.execute(query)
            existing_supervisor = result.scalars().first()
            
            if existing_supervisor:
                # Remove supervisor status from the existing supervisor
                existing_supervisor.is_supervisor = False
                await db.flush()
        
        # Update attributes
        update_data = agent_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(agent, key, value)
        
        await db.flush()
        return agent
    
    @staticmethod
    async def delete_agent(db: AsyncSession, agent_id: uuid.UUID) -> bool:
        """Delete an agent"""
        agent = await AgentService.get_agent(db, agent_id)
        if not agent:
            return False
        
        await db.delete(agent)
        await db.flush()
        return True
    
    @staticmethod
    async def assign_tool_to_agent(
        db: AsyncSession, agent_id: uuid.UUID, tool_id: uuid.UUID, settings: Dict[str, Any] = None
    ) -> bool:
        """Assign an MCP tool to an agent"""
        # Check if agent and tool exist
        agent = await AgentService.get_agent(db, agent_id)
        tool = await MCPServerService.get_tool(db, tool_id)
        
        if not agent or not tool:
            return False
        
        # Create agent tool association
        agent_tool = AgentTool(
            agent_id=agent_id,
            mcp_tool_id=tool_id,
            settings=settings or {},
            is_enabled=True
        )
        
        db.add(agent_tool)
        await db.flush()
        return True
    
    @staticmethod
    async def remove_tool_from_agent(
        db: AsyncSession, agent_id: uuid.UUID, tool_id: uuid.UUID
    ) -> bool:
        """Remove an MCP tool from an agent"""
        query = select(AgentTool).where(
            (AgentTool.agent_id == agent_id) & 
            (AgentTool.mcp_tool_id == tool_id)
        )
        result = await db.execute(query)
        agent_tool = result.scalars().first()
        
        if not agent_tool:
            return False
        
        await db.delete(agent_tool)
        await db.flush()
        return True


class MCPServerService:
    """Service for MCP server-related operations"""
    
    @staticmethod
    async def get_servers(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[MCPServer]:
        """Get all MCP servers with pagination"""
        query = select(MCPServer).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_server(db: AsyncSession, server_id: uuid.UUID) -> Optional[MCPServer]:
        """Get an MCP server by ID"""
        query = select(MCPServer).where(MCPServer.id == server_id)
        result = await db.execute(query)
        return result.scalars().first()
    
    @staticmethod
    async def get_server_by_url(db: AsyncSession, url: str) -> Optional[MCPServer]:
        """Get an MCP server by URL"""
        query = select(MCPServer).where(MCPServer.url == url)
        result = await db.execute(query)
        return result.scalars().first()
    
    @staticmethod
    async def create_server(db: AsyncSession, server_data: dict) -> MCPServer:
        """Create a new MCP server"""
        server = MCPServer(**server_data)
        db.add(server)
        await db.flush()
        return server
    
    @staticmethod
    async def update_server(
        db: AsyncSession, server_id: uuid.UUID, server_data: dict
    ) -> Optional[MCPServer]:
        """Update an MCP server"""
        server = await MCPServerService.get_server(db, server_id)
        if not server:
            return None
        
        for key, value in server_data.items():
            setattr(server, key, value)
        
        await db.flush()
        return server
    
    @staticmethod
    async def delete_server(db: AsyncSession, server_id: uuid.UUID) -> bool:
        """Delete an MCP server"""
        server = await MCPServerService.get_server(db, server_id)
        if not server:
            return False
        
        await db.delete(server)
        await db.flush()
        return True
    
    @staticmethod
    async def get_tools(db: AsyncSession, server_id: uuid.UUID) -> List[MCPTool]:
        """Get all tools for an MCP server"""
        query = select(MCPTool).where(MCPTool.mcp_server_id == server_id)
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_tool(db: AsyncSession, tool_id: uuid.UUID) -> Optional[MCPTool]:
        """Get an MCP tool by ID"""
        query = select(MCPTool).where(MCPTool.id == tool_id)
        result = await db.execute(query)
        return result.scalars().first()
    
    @staticmethod
    async def create_tool(db: AsyncSession, tool_data: dict) -> MCPTool:
        """Create a new MCP tool"""
        tool = MCPTool(**tool_data)
        db.add(tool)
        await db.flush()
        return tool
    
    @staticmethod
    async def update_tool(
        db: AsyncSession, tool_id: uuid.UUID, tool_data: dict
    ) -> Optional[MCPTool]:
        """Update an MCP tool"""
        tool = await MCPServerService.get_tool(db, tool_id)
        if not tool:
            return None
        
        for key, value in tool_data.items():
            setattr(tool, key, value)
        
        await db.flush()
        return tool
    
    @staticmethod
    async def delete_tool(db: AsyncSession, tool_id: uuid.UUID) -> bool:
        """Delete an MCP tool"""
        tool = await MCPServerService.get_tool(db, tool_id)
        if not tool:
            return False
        
        await db.delete(tool)
        await db.flush()
        return True
