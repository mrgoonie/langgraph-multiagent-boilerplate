"""
Service for managing conversations and messages
"""
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message, MessageRole, MessageStatus
from app.models.crew import Crew, Agent
from app.models.activity_log import ActivityLog, ActivityType


class ConversationService:
    """Service for conversation-related operations"""
    
    @staticmethod
    async def get_conversations(
        db: AsyncSession, 
        user_id: str = None, 
        crew_id: uuid.UUID = None,
        skip: int = 0, 
        limit: int = 100
    ) -> List[Conversation]:
        """Get conversations with filters and pagination"""
        query = select(Conversation)
        
        # Apply filters if provided
        if user_id:
            query = query.where(Conversation.user_id == user_id)
        if crew_id:
            query = query.where(Conversation.crew_id == crew_id)
        
        query = query.order_by(Conversation.updated_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_conversation(db: AsyncSession, conversation_id: uuid.UUID) -> Optional[Conversation]:
        """Get a conversation by ID"""
        query = select(Conversation).where(Conversation.id == conversation_id)
        result = await db.execute(query)
        return result.scalars().first()
    
    @staticmethod
    async def create_conversation(
        db: AsyncSession, 
        user_id: str, 
        crew_id: uuid.UUID,
        title: str = None,
        metadata: Dict[str, Any] = None
    ) -> Conversation:
        """Create a new conversation"""
        conversation = Conversation(
            user_id=user_id,
            crew_id=crew_id,
            title=title,
            metadata=metadata or {},
            is_active=True
        )
        db.add(conversation)
        await db.flush()
        return conversation
    
    @staticmethod
    async def update_conversation(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        title: str = None,
        metadata: Dict[str, Any] = None,
        is_active: bool = None
    ) -> Optional[Conversation]:
        """Update a conversation"""
        conversation = await ConversationService.get_conversation(db, conversation_id)
        if not conversation:
            return None
        
        # Update fields if provided
        if title is not None:
            conversation.title = title
        if metadata is not None:
            conversation.metadata = metadata
        if is_active is not None:
            conversation.is_active = is_active
        
        await db.flush()
        return conversation
    
    @staticmethod
    async def delete_conversation(db: AsyncSession, conversation_id: uuid.UUID) -> bool:
        """Delete a conversation"""
        conversation = await ConversationService.get_conversation(db, conversation_id)
        if not conversation:
            return False
        
        await db.delete(conversation)
        await db.flush()
        return True
    
    @staticmethod
    async def add_message(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        role: MessageRole,
        content: str,
        agent_id: uuid.UUID = None,
        parent_id: uuid.UUID = None,
        status: MessageStatus = MessageStatus.COMPLETED,
        metadata: Dict[str, Any] = None
    ) -> Optional[Message]:
        """Add a new message to a conversation"""
        # Check if conversation exists
        conversation = await ConversationService.get_conversation(db, conversation_id)
        if not conversation:
            return None
        
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            agent_id=agent_id,
            parent_id=parent_id,
            status=status,
            metadata=metadata or {}
        )
        
        db.add(message)
        
        # Update conversation timestamp
        conversation.updated_at = datetime.utcnow()
        
        await db.flush()
        return message
    
    @staticmethod
    async def get_messages(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Message]:
        """Get messages for a conversation"""
        query = select(Message).where(Message.conversation_id == conversation_id)
        query = query.order_by(Message.created_at).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_message(db: AsyncSession, message_id: uuid.UUID) -> Optional[Message]:
        """Get a message by ID"""
        query = select(Message).where(Message.id == message_id)
        result = await db.execute(query)
        return result.scalars().first()
    
    @staticmethod
    async def update_message_status(
        db: AsyncSession,
        message_id: uuid.UUID,
        status: MessageStatus,
        metadata: Dict[str, Any] = None
    ) -> Optional[Message]:
        """Update a message status"""
        message = await ConversationService.get_message(db, message_id)
        if not message:
            return None
        
        message.status = status
        if metadata:
            # Update metadata without overwriting existing values
            message.metadata.update(metadata)
        
        await db.flush()
        return message


class ActivityLogService:
    """Service for activity log operations"""
    
    @staticmethod
    async def log_activity(
        db: AsyncSession,
        agent_id: uuid.UUID,
        activity_type: ActivityType,
        description: str,
        conversation_id: uuid.UUID = None,
        message_id: uuid.UUID = None,
        details: Dict[str, Any] = None
    ) -> ActivityLog:
        """Create a new activity log entry"""
        log = ActivityLog(
            agent_id=agent_id,
            activity_type=activity_type,
            description=description,
            conversation_id=conversation_id,
            message_id=message_id,
            details=details or {}
        )
        
        db.add(log)
        await db.flush()
        return log
    
    @staticmethod
    async def get_activity_logs(
        db: AsyncSession,
        agent_id: uuid.UUID = None,
        conversation_id: uuid.UUID = None,
        activity_type: ActivityType = None,
        start_time: datetime = None,
        end_time: datetime = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ActivityLog]:
        """Get activity logs with filters"""
        query = select(ActivityLog)
        
        # Apply filters
        if agent_id:
            query = query.where(ActivityLog.agent_id == agent_id)
        if conversation_id:
            query = query.where(ActivityLog.conversation_id == conversation_id)
        if activity_type:
            query = query.where(ActivityLog.activity_type == activity_type)
        if start_time:
            query = query.where(ActivityLog.created_at >= start_time)
        if end_time:
            query = query.where(ActivityLog.created_at <= end_time)
        
        query = query.order_by(ActivityLog.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())
