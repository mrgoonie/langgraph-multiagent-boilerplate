"""
Pydantic schemas for conversations and messages
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from app.models.conversation import MessageRole, MessageStatus


# Base schemas
class ConversationBase(BaseModel):
    """Base schema for conversation data"""
    user_id: str
    title: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MessageBase(BaseModel):
    """Base schema for message data"""
    role: MessageRole
    content: str
    agent_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    status: MessageStatus = MessageStatus.COMPLETED
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Create schemas
class ConversationCreate(ConversationBase):
    """Schema for creating a new conversation"""
    crew_id: UUID


class MessageCreate(MessageBase):
    """Schema for creating a new message"""
    pass


# Response schemas
class ConversationResponse(ConversationBase):
    """Schema for conversation response"""
    id: UUID
    crew_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class MessageResponse(MessageBase):
    """Schema for message response"""
    id: UUID
    conversation_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ConversationWithMessages(ConversationResponse):
    """Conversation schema with included messages"""
    messages: List[MessageResponse] = Field(default_factory=list)


# Update schemas
class ConversationUpdate(BaseModel):
    """Schema for updating a conversation"""
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class MessageUpdate(BaseModel):
    """Schema for updating a message"""
    content: Optional[str] = None
    status: Optional[MessageStatus] = None
    metadata: Optional[Dict[str, Any]] = None


# Chat schemas
class ChatRequest(BaseModel):
    """Schema for a chat request"""
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """Schema for a chat response"""
    message_id: UUID
    content: str
