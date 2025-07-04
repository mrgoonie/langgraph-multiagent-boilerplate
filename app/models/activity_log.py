"""
Database models for activity logs
"""
import enum
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, relationship, mapped_column

from app.db.base import Base


class ActivityType(enum.Enum):
    """Types of activities that can be logged"""
    TOOL_CALL = "tool_call"
    AGENT_MESSAGE = "agent_message"
    PLAN_CREATION = "plan_creation"
    TASK_ASSIGNMENT = "task_assignment"
    TASK_COMPLETION = "task_completion"
    ERROR = "error"
    STATUS_CHANGE = "status_change"
    CUSTOM = "custom"


class ActivityLog(Base):
    """Model for logging agent activities"""
    __tablename__ = "activity_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=Base.generate_uuid
    )
    activity_type: Mapped[ActivityType] = mapped_column(
        Enum(ActivityType), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Foreign keys
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    
    # Additional data in JSON format
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    
    # Relationships
    agent = relationship("Agent", back_populates="activity_logs")
    conversation = relationship("Conversation", backref="activity_logs")
    message = relationship("Message", backref="activity_logs")
