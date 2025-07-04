"""
API routes for crews and agents management
"""
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.services.crew_service import CrewService, AgentService
from app.schemas.crew import (
    CrewCreate, 
    CrewUpdate, 
    CrewResponse, 
    CrewWithAgentsAndServers,
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentWithTools
)


router = APIRouter()

# Crew routes
crews_router = APIRouter(prefix="/crews", tags=["crews"])

@crews_router.get("/", response_model=List[CrewResponse])
async def get_crews(
    skip: int = 0, 
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get a list of all crews"""
    crews = await CrewService.get_crews(db, skip=skip, limit=limit)
    return crews


@crews_router.post("/", response_model=CrewResponse, status_code=status.HTTP_201_CREATED)
async def create_crew(
    crew: CrewCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new crew"""
    db_crew = await CrewService.create_crew(db, crew)
    return db_crew


@crews_router.get("/{crew_id}", response_model=CrewWithAgentsAndServers)
async def get_crew(
    crew_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific crew by ID"""
    crew = await CrewService.get_crew(db, crew_id)
    if not crew:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crew with ID {crew_id} not found"
        )
    return crew


@crews_router.put("/{crew_id}", response_model=CrewResponse)
async def update_crew(
    crew_id: uuid.UUID,
    crew_update: CrewUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a crew"""
    updated_crew = await CrewService.update_crew(db, crew_id, crew_update)
    if not updated_crew:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crew with ID {crew_id} not found"
        )
    return updated_crew


@crews_router.delete("/{crew_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_crew(
    crew_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a crew"""
    success = await CrewService.delete_crew(db, crew_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crew with ID {crew_id} not found"
        )
    return None


# Agent routes
agents_router = APIRouter(prefix="/agents", tags=["agents"])

@agents_router.get("/", response_model=List[AgentResponse])
async def get_agents(
    crew_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get a list of all agents, optionally filtered by crew"""
    agents = await AgentService.get_agents(db, crew_id=crew_id)
    return agents


@agents_router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent: AgentCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new agent"""
    # Verify the crew exists
    crew = await CrewService.get_crew(db, agent.crew_id)
    if not crew:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crew with ID {agent.crew_id} not found"
        )
    
    db_agent = await AgentService.create_agent(db, agent)
    return db_agent


@agents_router.get("/{agent_id}", response_model=AgentWithTools)
async def get_agent(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific agent by ID"""
    agent = await AgentService.get_agent(db, agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found"
        )
    return agent


@agents_router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: uuid.UUID,
    agent_update: AgentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an agent"""
    updated_agent = await AgentService.update_agent(db, agent_id, agent_update)
    if not updated_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found"
        )
    return updated_agent


@agents_router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete an agent"""
    success = await AgentService.delete_agent(db, agent_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found"
        )
    return None


# Add agent tool management routes
@agents_router.post("/{agent_id}/tools/{tool_id}", status_code=status.HTTP_201_CREATED)
async def assign_tool_to_agent(
    agent_id: uuid.UUID,
    tool_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Assign an MCP tool to an agent"""
    success = await AgentService.assign_tool_to_agent(db, agent_id, tool_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent or tool not found"
        )
    return {"status": "Tool assigned successfully"}


@agents_router.delete("/{agent_id}/tools/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_tool_from_agent(
    agent_id: uuid.UUID,
    tool_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Remove an MCP tool from an agent"""
    success = await AgentService.remove_tool_from_agent(db, agent_id, tool_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent or tool not found, or tool is not assigned to agent"
        )
    return None


# Add crew routes to main router
router.include_router(crews_router)
router.include_router(agents_router)
