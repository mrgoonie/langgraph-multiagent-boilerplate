"""
Tests for the conversation API endpoints, focusing on OpenRouter API integration
"""
import pytest
import asyncio
import uuid
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

from app.main import app
from app.models.conversation import MessageRole, MessageStatus
from app.schemas.conversation import ChatRequest

client = TestClient(app)

# Mock data
mock_conversation_id = uuid.uuid4()
mock_crew_id = uuid.uuid4()
mock_user_id = "test-user-123"
mock_agent_id = uuid.uuid4()


@pytest.fixture
def mock_services():
    """Fixture to set up mocks for services used in the API endpoints"""
    with patch("app.api.routes.conversation.ConversationService") as mock_conversation_service, \
         patch("app.api.routes.conversation.CrewService") as mock_crew_service, \
         patch("app.api.routes.conversation.AgentService") as mock_agent_service, \
         patch("app.api.routes.conversation.ActivityLogService") as mock_activity_log_service, \
         patch("app.api.routes.conversation.ai_provider") as mock_ai_provider:

        # Setup mock conversation service
        mock_conversation = MagicMock()
        mock_conversation.id = mock_conversation_id
        mock_conversation.crew_id = mock_crew_id
        mock_conversation.user_id = mock_user_id
        # Use AsyncMock for async methods
        mock_conversation_service.get_conversation = AsyncMock(return_value=mock_conversation)

        # Setup mock message
        mock_message = MagicMock()
        mock_message.id = uuid.uuid4()
        mock_message.content = "Test message"
        # Use AsyncMock for async methods
        mock_conversation_service.add_message = AsyncMock(return_value=mock_message)
        mock_conversation_service.get_messages = AsyncMock(return_value=[])

        # Setup mock crew service
        mock_crew = MagicMock()
        mock_crew.id = mock_crew_id
        mock_crew.name = "Test Crew"
        # Use AsyncMock for async methods
        mock_crew_service.get_crew = AsyncMock(return_value=mock_crew)

        # Setup mock agent service
        mock_agent = MagicMock()
        mock_agent.id = mock_agent_id
        mock_agent.name = "Supervisor"
        mock_agent.is_supervisor = True
        mock_agent.model = "openai/gpt-4-turbo"
        # Use AsyncMock for async methods
        mock_agent_service.get_agents = AsyncMock(return_value=[mock_agent])

        # Setup mock AI provider
        mock_model = MagicMock()
        mock_model.invoke = AsyncMock(return_value=MagicMock(content="Test AI response"))
        mock_model.ainvoke = AsyncMock(return_value=MagicMock(content="Test AI response"))
        mock_ai_provider.get_model.return_value = mock_model

        # Setup activity log service
        mock_activity_log_service.log_activity = AsyncMock()
        
        yield {
            "conversation_service": mock_conversation_service,
            "crew_service": mock_crew_service,
            "agent_service": mock_agent_service,
            "activity_log_service": mock_activity_log_service,
            "ai_provider": mock_ai_provider
        }


@pytest.mark.asyncio
async def test_chat_endpoint(mock_services):
    """Test the non-streaming chat endpoint with mock OpenRouter API"""
    
    # Prepare request
    request_data = {
        "message": "Hello, this is a test message"
    }
    
    # Make the API call
    response = client.post(
        f"/api/conversations/{mock_conversation_id}/chat",
        json=request_data
    )
    
    # Assert response
    assert response.status_code == 200
    response_data = response.json()
    assert "message_id" in response_data
    assert "content" in response_data
    assert "created_at" in response_data
    
    # Verify the AI provider was called correctly
    mock_services["ai_provider"].get_model.assert_called_once()
    assert not mock_services["ai_provider"].get_model.call_args[1]["streaming"]
    
    # Verify conversation service methods were called
    mock_services["conversation_service"].get_conversation.assert_called_once()
    mock_services["conversation_service"].add_message.assert_called()


@pytest.mark.asyncio
async def test_chat_stream_endpoint(mock_services):
    """Test the streaming chat endpoint with mock OpenRouter API"""
    
    # Setup streaming mock
    async def mock_stream():
        # Simulate chunks from streaming API
        chunks = [
            MagicMock(content="This "),
            MagicMock(content="is "),
            MagicMock(content="a "),
            MagicMock(content="streaming "),
            MagicMock(content="response.")
        ]
        for chunk in chunks:
            yield chunk
    
    # Configure mock to return streamable object
    mock_services["ai_provider"].get_model.return_value.astream = AsyncMock(
        return_value=mock_stream()
    )
    
    # Prepare request
    request_data = {
        "message": "Hello, stream a response"
    }
    
    # Make the API call
    with client.stream(
        "POST",
        f"/api/conversations/{mock_conversation_id}/chat/stream",
        json=request_data
    ) as response:
        # Check status code
        assert response.status_code == 200
        
        # Read and check all streaming chunks
        content = b""
        for chunk in response.iter_bytes():
            content += chunk
        
        # Convert bytes to string and check contents
        content_str = content.decode('utf-8')
        assert "data:" in content_str
        assert "chat.completion.chunk" in content_str
        assert "content" in content_str
    
    # Verify the AI provider was called with streaming=True
    mock_services["ai_provider"].get_model.assert_called_once()
    assert mock_services["ai_provider"].get_model.call_args[1]["streaming"] is True


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
