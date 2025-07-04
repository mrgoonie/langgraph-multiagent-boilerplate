"""
Database models for conversations and messages
"""
import enum
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, relationship, mapped_column

from app.db.base import Base


class MessageRole(enum.Enum):
    """Message sender role types"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    AGENT = "agent"  # Messages from specific agents in the crew


class MessageStatus(enum.Enum):
    """Status of a message in a conversation"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Conversation(Base):
    """Model for conversations between users and AI crews"""
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=Base.generate_uuid
    )
    title: Mapped[str] = mapped_column(String(255), nullable=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # Foreign keys
    crew_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crews.id", ondelete="CASCADE"), nullable=False
    )
    
    # Metadata
    meta_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # Relationships
    crew: Mapped["Crew"] = relationship("Crew", back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan", 
        order_by="Message.created_at"
    )
    
    @property
    def last_message(self) -> Optional["Message"]:
        """Get the last message in the conversation"""
        if not self.messages:
            return None
        return self.messages[-1]
    
    @property
    def last_user_message(self) -> Optional["Message"]:
        """Get the last user message in the conversation"""
        for message in reversed(self.messages):
            if message.role == MessageRole.USER:
                return message
        return None


class Message(Base):
    """Model for individual messages in a conversation"""
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=Base.generate_uuid
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # For agent-specific messages
    agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )
    
    # Message status for tracking processing
    status: Mapped[MessageStatus] = mapped_column(
        Enum(MessageStatus), default=MessageStatus.COMPLETED, nullable=False
    )
    
    # Metadata for additional information (tokens, processing info, etc.)
    meta_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    # Foreign keys
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    
    # References to parent messages in a thread
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )
    parent: Mapped[Optional["Message"]] = relationship(
        "Message", remote_side=[id], backref="replies"
    )
    agent = relationship("Agent", backref="messages")
