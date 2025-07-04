"""
API routes for conversations and chat functionality
"""
from typing import List, Optional, Dict, Any
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.db.base import get_db
from app.models.conversation import MessageRole, MessageStatus
from app.models.activity_log import ActivityType
from app.services.conversation_service import ConversationService, ActivityLogService
from app.services.crew_service import CrewService, AgentService
from app.core.langgraph.supervisor import create_supervisor_graph
from app.services.ai_provider import ai_provider
from app.schemas.crew import CrewResponse, AgentResponse
from app.schemas.conversation import (
    ConversationCreate, 
    ConversationResponse, 
    ConversationUpdate,
    MessageCreate,
    MessageResponse,
    ChatRequest,
    ChatResponse,
)


router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("/", response_model=List[ConversationResponse])
async def get_conversations(
    user_id: Optional[str] = None,
    crew_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Get a list of conversations with optional filters"""
    conversations = await ConversationService.get_conversations(
        db, user_id=user_id, crew_id=crew_id, skip=skip, limit=limit
    )
    return conversations


@router.post("/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation: ConversationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversation"""
    # Verify the crew exists
    crew = await CrewService.get_crew(db, conversation.crew_id)
    if not crew:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crew with ID {conversation.crew_id} not found"
        )
    
    # Create the conversation
    db_conversation = await ConversationService.create_conversation(
        db=db,
        user_id=conversation.user_id,
        crew_id=conversation.crew_id,
        title=conversation.title,
        metadata=conversation.metadata,
    )
    
    return db_conversation


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific conversation by ID"""
    conversation = await ConversationService.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID {conversation_id} not found"
        )
    
    return conversation


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: uuid.UUID,
    conversation_update: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a conversation"""
    updated_conversation = await ConversationService.update_conversation(
        db=db,
        conversation_id=conversation_id,
        title=conversation_update.title,
        metadata=conversation_update.metadata,
        is_active=conversation_update.is_active,
    )
    
    if not updated_conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID {conversation_id} not found"
        )
    
    return updated_conversation


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation"""
    success = await ConversationService.delete_conversation(db, conversation_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID {conversation_id} not found"
        )
    return None


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Get messages for a specific conversation"""
    # Verify conversation exists
    conversation = await ConversationService.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID {conversation_id} not found"
        )
    
    messages = await ConversationService.get_messages(
        db, conversation_id, skip=skip, limit=limit
    )
    return messages


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def add_message(
    conversation_id: uuid.UUID,
    message: MessageCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a message to a conversation"""
    # Verify conversation exists
    conversation = await ConversationService.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID {conversation_id} not found"
        )
    
    # Add the message
    db_message = await ConversationService.add_message(
        db=db,
        conversation_id=conversation_id,
        role=message.role,
        content=message.content,
        agent_id=message.agent_id,
        parent_id=message.parent_id,
        status=message.status,
        metadata=message.metadata,
    )
    
    # Log activity if it's an agent message
    if message.role == MessageRole.AGENT and message.agent_id:
        await ActivityLogService.log_activity(
            db=db,
            agent_id=message.agent_id,
            activity_type=ActivityType.AGENT_MESSAGE,
            description=f"Agent sent message in conversation {conversation_id}",
            conversation_id=conversation_id,
            message_id=db_message.id,
            details={"content_length": len(message.content)}
        )
    
    return db_message


@router.post("/{conversation_id}/chat", response_model=ChatResponse)
async def chat(
    conversation_id: uuid.UUID,
    chat_request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Send a message to the crew and get a response"""
    # Verify conversation exists
    conversation = await ConversationService.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID {conversation_id} not found"
        )
    
    # Get crew and agents
    crew = await CrewService.get_crew(db, conversation.crew_id)
    if not crew:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crew with ID {conversation.crew_id} not found"
        )
    
    agents = await AgentService.get_agents(db, crew_id=crew.id)
    
    # Find supervisor agent
    supervisor = None
    for agent in agents:
        if agent.is_supervisor:
            supervisor = agent
            break
    
    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No supervisor agent found for crew {crew.id}"
        )
    
    # Add user message to conversation
    user_message = await ConversationService.add_message(
        db=db,
        conversation_id=conversation_id,
        role=MessageRole.USER,
        content=chat_request.message,
        status=MessageStatus.COMPLETED,
    )
    
    # Process non-streaming chat request using real OpenRouter API
    # Get message history for context
    messages = await ConversationService.get_messages(db, conversation_id)
    
    # Format messages for the LLM
    formatted_messages = []
    # Add previous messages to context (limit to recent messages for context window)
    for msg in messages[-10:]:  # Include only the 10 most recent messages
        if msg.role == MessageRole.USER:
            formatted_messages.append({"role": "user", "content": msg.content})
        elif msg.role == MessageRole.ASSISTANT:
            formatted_messages.append({"role": "assistant", "content": msg.content})
    
    # Create the LLM chain using the AIProvider
    model = ai_provider.get_model(
        model_name=supervisor.model,
        temperature=0.7,  # Use moderate temperature for creative responses
        streaming=False
    )
    
    try:
        # Invoke the model with the conversation history and current message
        response = await model.ainvoke(formatted_messages + [{"role": "user", "content": chat_request.message}])
        response_content = response.content
    except Exception as e:
        # Log the error
        print(f"Error calling OpenRouter API: {str(e)}")
        # Provide a fallback response
        response_content = f"I apologize, but I encountered an issue processing your request. Please try again later."
        # You may want to log this to your monitoring system
    
    # Add assistant message to conversation
    assistant_message = await ConversationService.add_message(
        db=db,
        conversation_id=conversation_id,
        role=MessageRole.ASSISTANT,
        content=response_content,
        agent_id=supervisor.id,
        parent_id=user_message.id,
        status=MessageStatus.COMPLETED,
    )
    
    # Log the activity
    await ActivityLogService.log_activity(
        db=db,
        agent_id=supervisor.id,
        activity_type=ActivityType.AGENT_MESSAGE,
        description=f"Supervisor responded in conversation {conversation_id}",
        conversation_id=conversation_id,
        message_id=assistant_message.id,
    )
    
    return ChatResponse(
        message_id=assistant_message.id,
        content=response_content
    )


@router.post("/{conversation_id}/chat/stream")
async def chat_stream(
    conversation_id: uuid.UUID,
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send a message to the crew and get a streaming response"""
    # Verify conversation exists
    conversation = await ConversationService.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with ID {conversation_id} not found"
        )
    
    # Get crew and supervisor agent
    crew = await CrewService.get_crew(db, conversation.crew_id)
    if not crew:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crew with ID {conversation.crew_id} not found"
        )
    
    # Find supervisor agent
    agents = await AgentService.get_agents(db, crew_id=crew.id)
    supervisor = None
    for agent in agents:
        if agent.is_supervisor:
            supervisor = agent
            break
    
    if not supervisor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No supervisor agent found for crew {crew.id}"
        )
    
    # Add user message to conversation
    user_message = await ConversationService.add_message(
        db=db,
        conversation_id=conversation_id,
        role=MessageRole.USER,
        content=chat_request.message,
        status=MessageStatus.COMPLETED,
    )
    
    # Create a placeholder for assistant message
    assistant_message = await ConversationService.add_message(
        db=db,
        conversation_id=conversation_id,
        role=MessageRole.ASSISTANT,
        content="",
        agent_id=supervisor.id,
        parent_id=user_message.id,
        status=MessageStatus.PROCESSING,
    )
    
    # Real streaming response generation using OpenRouter API
    async def stream_response():
        message_id = str(assistant_message.id)
        content_so_far = ""
        
        try:
            # Get message history for context
            messages = await ConversationService.get_messages(db, conversation_id)
            
            # Format messages for the LLM
            formatted_messages = []
            # Add previous messages to context (limit to recent messages)
            for msg in messages[-10:]:  # Include only the 10 most recent messages
                if msg.role == MessageRole.USER:
                    formatted_messages.append({"role": "user", "content": msg.content})
                elif msg.role == MessageRole.ASSISTANT:
                    formatted_messages.append({"role": "assistant", "content": msg.content})
                    
            # Add the current message
            formatted_messages.append({"role": "user", "content": chat_request.message})
            
            # Create the LLM model with streaming enabled
            model = ai_provider.get_model(
                model_name=supervisor.model,
                temperature=0.7,  # Use moderate temperature for creative responses
                streaming=True  # Enable streaming
            )
            
            # Stream the response from OpenRouter
            async for chunk in await model.astream(formatted_messages):
                if hasattr(chunk, 'content') and chunk.content is not None:
                    content_so_far += chunk.content
                    
                    # Format the chunk data for SSE
                    data = {
                        "id": message_id,
                        "object": "chat.completion.chunk",
                        "created": int(assistant_message.created_at.timestamp()),
                        "model": supervisor.model,
                        "choices": [
                            {
                                "delta": {"content": chunk.content},
                                "index": 0,
                                "finish_reason": None
                            }
                        ]
                    }
                    yield f"data: {json.dumps(data)}\n\n"
            
            # Send final chunk with finish_reason: "stop"
            data = {
                "id": message_id,
                "object": "chat.completion.chunk",
                "created": int(assistant_message.created_at.timestamp()),
                "model": supervisor.model,
                "choices": [
                    {
                        "delta": {},
                        "index": 0,
                        "finish_reason": "stop"
                    }
                ]
            }
            yield f"data: {json.dumps(data)}\n\n"
            
        except Exception as e:
            # Log the error
            print(f"Error during streaming response: {str(e)}")
            
            # Send error message to the client
            error_msg = "I apologize, but I encountered an issue processing your request. Please try again later."
            content_so_far = error_msg
            
            # Format error as a streaming chunk
            data = {
                "id": message_id,
                "object": "chat.completion.chunk",
                "created": int(assistant_message.created_at.timestamp()),
                "model": supervisor.model,
                "choices": [
                    {
                        "delta": {"content": error_msg},
                        "index": 0,
                        "finish_reason": "error"
                    }
                ]
            }
            yield f"data: {json.dumps(data)}\n\n"
            
            # Send final chunk
            data = {
                "id": message_id,
                "object": "chat.completion.chunk",
                "created": int(assistant_message.created_at.timestamp()),
                "model": supervisor.model,
                "choices": [
                    {
                        "delta": {},
                        "index": 0,
                        "finish_reason": "stop"
                    }
                ]
            }
            yield f"data: {json.dumps(data)}\n\n"
        
        # After streaming is complete (whether success or error), update the message in the database
        
        # Update the message in the database with the complete content
        await ConversationService.update_message_status(
            db=db,
            message_id=assistant_message.id,
            status=MessageStatus.COMPLETED,
            metadata={"final_content": content_so_far}
        )
        
        # Update the message content
        assistant_message.content = content_so_far
        await db.commit()
        
        # Log the activity
        await ActivityLogService.log_activity(
            db=db,
            agent_id=supervisor.id,
            activity_type=ActivityType.AGENT_MESSAGE,
            description=f"Supervisor responded in conversation {conversation_id} (streaming)",
            conversation_id=conversation_id,
            message_id=assistant_message.id,
        )
        
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream"
    )
