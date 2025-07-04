"""
Tests for the agent service
"""
import pytest
import uuid
from uuid import UUID
import asyncio
from typing import List, Dict, Any

from app.services.crew_service import AgentService
from app.schemas.crew import AgentCreate, AgentUpdate
from app.models.crew import Agent


@pytest.mark.asyncio
async def test_create_agent(db_session, test_crew):
    """Test creating an agent"""
    # Create agent data
    agent_data = AgentCreate(
        crew_id=test_crew.id,
        name="Test Agent Creation",
        description="An agent created during testing",
        system_prompt="You are a test agent created for unit tests",
        model="test-model",
        is_supervisor=False,
        metadata={"test_key": "test_value"}
    )
    
    # Create the agent
    agent = await AgentService.create_agent(db_session, agent_data)
    
    # Verify the agent was created with the correct data
    assert agent.id is not None
    assert agent.name == agent_data.name
    assert agent.description == agent_data.description
    assert agent.system_prompt == agent_data.system_prompt
    assert agent.model == agent_data.model
    assert agent.is_supervisor == agent_data.is_supervisor
    assert agent.metadata == agent_data.metadata
    assert agent.crew_id == test_crew.id


@pytest.mark.asyncio
async def test_get_agent(db_session, test_agent):
    """Test retrieving an agent by ID"""
    # Get the agent
    retrieved_agent = await AgentService.get_agent(db_session, test_agent.id)
    
    # Verify the retrieved agent matches the test agent
    assert retrieved_agent is not None
    assert retrieved_agent.id == test_agent.id
    assert retrieved_agent.name == test_agent.name
    assert retrieved_agent.description == test_agent.description
    assert retrieved_agent.system_prompt == test_agent.system_prompt
    assert retrieved_agent.model == test_agent.model
    assert retrieved_agent.is_supervisor == test_agent.is_supervisor
    assert retrieved_agent.metadata == test_agent.metadata
    assert retrieved_agent.crew_id == test_agent.crew_id


@pytest.mark.asyncio
async def test_get_agents(db_session, test_agent, test_crew):
    """Test retrieving all agents"""
    # Create a second agent
    second_agent_data = AgentCreate(
        crew_id=test_crew.id,
        name="Second Test Agent",
        description="Another agent for testing",
        system_prompt="You are another test agent",
        model="test-model",
        is_supervisor=False,
        metadata={"test": True}
    )
    second_agent = await AgentService.create_agent(db_session, second_agent_data)
    
    # Get all agents
    agents = await AgentService.get_agents(db_session)
    
    # Verify both agents are retrieved
    assert len(agents) >= 2
    agent_ids = [agent.id for agent in agents]
    assert test_agent.id in agent_ids
    assert second_agent.id in agent_ids
    
    # Test filtering by crew
    crew_agents = await AgentService.get_agents(db_session, crew_id=test_crew.id)
    crew_agent_ids = [agent.id for agent in crew_agents]
    assert test_agent.id in crew_agent_ids
    assert second_agent.id in crew_agent_ids


@pytest.mark.asyncio
async def test_update_agent(db_session, test_agent):
    """Test updating an agent"""
    # Create update data
    update_data = AgentUpdate(
        name="Updated Test Agent",
        description="Updated description",
        system_prompt="You are an updated test agent",
        model="updated-model",
        is_supervisor=True,
        metadata={"updated": True}
    )
    
    # Update the agent
    updated_agent = await AgentService.update_agent(db_session, test_agent.id, update_data)
    
    # Verify the agent was updated correctly
    assert updated_agent is not None
    assert updated_agent.id == test_agent.id
    assert updated_agent.name == update_data.name
    assert updated_agent.description == update_data.description
    assert updated_agent.system_prompt == update_data.system_prompt
    assert updated_agent.model == update_data.model
    assert updated_agent.is_supervisor == update_data.is_supervisor
    assert updated_agent.metadata == update_data.metadata


@pytest.mark.asyncio
async def test_delete_agent(db_session, test_agent):
    """Test deleting an agent"""
    # Delete the agent
    result = await AgentService.delete_agent(db_session, test_agent.id)
    
    # Verify deletion was successful
    assert result is True
    
    # Try to get the deleted agent
    deleted_agent = await AgentService.get_agent(db_session, test_agent.id)
    
    # Verify the agent is no longer found
    assert deleted_agent is None


@pytest.mark.asyncio
async def test_get_nonexistent_agent(db_session):
    """Test retrieving an agent that doesn't exist"""
    non_existent_id = uuid.uuid4()
    agent = await AgentService.get_agent(db_session, non_existent_id)
    assert agent is None


@pytest.mark.asyncio
async def test_update_nonexistent_agent(db_session):
    """Test updating an agent that doesn't exist"""
    non_existent_id = uuid.uuid4()
    update_data = AgentUpdate(name="This Agent Doesn't Exist")
    updated_agent = await AgentService.update_agent(db_session, non_existent_id, update_data)
    assert updated_agent is None


@pytest.mark.asyncio
async def test_delete_nonexistent_agent(db_session):
    """Test deleting an agent that doesn't exist"""
    non_existent_id = uuid.uuid4()
    result = await AgentService.delete_agent(db_session, non_existent_id)
    assert result is False


@pytest.mark.asyncio
async def test_assign_tool_to_agent(db_session, test_agent, test_mcp_tool):
    """Test assigning a tool to an agent"""
    # Assign the tool to the agent
    result = await AgentService.assign_tool_to_agent(
        db_session, test_agent.id, test_mcp_tool.id
    )
    
    # Verify assignment was successful
    assert result is True
    
    # Get the agent with tools
    agent_with_tools = await AgentService.get_agent(db_session, test_agent.id)
    
    # Verify the tool is assigned to the agent
    assert any(tool.id == test_mcp_tool.id for tool in agent_with_tools.tools)


@pytest.mark.asyncio
async def test_remove_tool_from_agent(db_session, test_agent, test_mcp_tool):
    """Test removing a tool from an agent"""
    # First, assign the tool
    await AgentService.assign_tool_to_agent(
        db_session, test_agent.id, test_mcp_tool.id
    )
    
    # Now remove the tool
    result = await AgentService.remove_tool_from_agent(
        db_session, test_agent.id, test_mcp_tool.id
    )
    
    # Verify removal was successful
    assert result is True
    
    # Get the agent with tools
    agent_with_tools = await AgentService.get_agent(db_session, test_agent.id)
    
    # Verify the tool is not assigned to the agent
    assert not any(tool.id == test_mcp_tool.id for tool in agent_with_tools.tools)
