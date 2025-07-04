"""
Tests for the crew service
"""
import pytest
import uuid
from uuid import UUID
import asyncio
from typing import List, Dict, Any

from app.services.crew_service import CrewService
from app.schemas.crew import CrewCreate, CrewUpdate, CrewResponse
from app.models.crew import Crew


@pytest.mark.asyncio
async def test_create_crew(db_session):
    """Test creating a crew"""
    # Create crew data
    crew_data = CrewCreate(
        name="Test Crew Creation",
        description="A crew created during testing",
        metadata={"test_key": "test_value"}
    )
    
    # Create the crew
    crew = await CrewService.create_crew(db_session, crew_data)
    
    # Verify the crew was created with the correct data
    assert crew.id is not None
    assert crew.name == crew_data.name
    assert crew.description == crew_data.description
    assert crew.metadata == crew_data.metadata


@pytest.mark.asyncio
async def test_get_crew(db_session, test_crew):
    """Test retrieving a crew by ID"""
    # Get the crew
    retrieved_crew = await CrewService.get_crew(db_session, test_crew.id)
    
    # Verify the retrieved crew matches the test crew
    assert retrieved_crew is not None
    assert retrieved_crew.id == test_crew.id
    assert retrieved_crew.name == test_crew.name
    assert retrieved_crew.description == test_crew.description
    assert retrieved_crew.metadata == test_crew.metadata


@pytest.mark.asyncio
async def test_get_crews(db_session, test_crew):
    """Test retrieving all crews"""
    # Create a second crew
    second_crew_data = CrewCreate(
        name="Second Test Crew",
        description="Another crew for testing",
        metadata={"test": True}
    )
    second_crew = await CrewService.create_crew(db_session, second_crew_data)
    
    # Get all crews
    crews = await CrewService.get_crews(db_session)
    
    # Verify both crews are retrieved
    assert len(crews) >= 2
    crew_ids = [crew.id for crew in crews]
    assert test_crew.id in crew_ids
    assert second_crew.id in crew_ids


@pytest.mark.asyncio
async def test_update_crew(db_session, test_crew):
    """Test updating a crew"""
    # Create update data
    update_data = CrewUpdate(
        name="Updated Test Crew",
        description="Updated description",
        metadata={"updated": True}
    )
    
    # Update the crew
    updated_crew = await CrewService.update_crew(db_session, test_crew.id, update_data)
    
    # Verify the crew was updated correctly
    assert updated_crew is not None
    assert updated_crew.id == test_crew.id
    assert updated_crew.name == update_data.name
    assert updated_crew.description == update_data.description
    assert updated_crew.metadata == update_data.metadata


@pytest.mark.asyncio
async def test_delete_crew(db_session, test_crew):
    """Test deleting a crew"""
    # Delete the crew
    result = await CrewService.delete_crew(db_session, test_crew.id)
    
    # Verify deletion was successful
    assert result is True
    
    # Try to get the deleted crew
    deleted_crew = await CrewService.get_crew(db_session, test_crew.id)
    
    # Verify the crew is no longer found
    assert deleted_crew is None


@pytest.mark.asyncio
async def test_get_nonexistent_crew(db_session):
    """Test retrieving a crew that doesn't exist"""
    non_existent_id = uuid.uuid4()
    crew = await CrewService.get_crew(db_session, non_existent_id)
    assert crew is None


@pytest.mark.asyncio
async def test_update_nonexistent_crew(db_session):
    """Test updating a crew that doesn't exist"""
    non_existent_id = uuid.uuid4()
    update_data = CrewUpdate(name="This Crew Doesn't Exist")
    updated_crew = await CrewService.update_crew(db_session, non_existent_id, update_data)
    assert updated_crew is None


@pytest.mark.asyncio
async def test_delete_nonexistent_crew(db_session):
    """Test deleting a crew that doesn't exist"""
    non_existent_id = uuid.uuid4()
    result = await CrewService.delete_crew(db_session, non_existent_id)
    assert result is False
