"""
AI Provider service for connecting to OpenRouter and other LLM APIs
"""
from typing import Any, Dict, List, Optional, Union
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from app.core.config import settings


class AIProvider:
    """Service for managing AI model connections and interactions"""
    
    def __init__(self):
        self.openrouter_models = {
            "google/gemini-2.5-flash": "gemini-2.5-flash",
            "google/gemini-2.5-pro": "gemini-2.5-pro",
        }
    
    def get_model(
        self,
        model_name: str = "google/gemini-2.5-flash",
        temperature: float = 0.2,
        streaming: bool = False,
        **kwargs
    ) -> BaseChatModel:
        """
        Get an AI model instance from OpenRouter or fallback to OpenAI directly
        
        Args:
            model_name: The model name/ID
            temperature: The sampling temperature (0-1)
            streaming: Whether to enable response streaming
            **kwargs: Additional model parameters
            
        Returns:
            A LangChain chat model instance
        """
        try:
            # Try using OpenRouter API first
            model = ChatOpenAI(
                model=model_name,
                temperature=temperature,
                streaming=streaming,
                api_key=settings.openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
                **kwargs
            )
            return model
        except Exception as e:
            # Fallback to OpenAI API directly if we have a key and it's an OpenAI model
            if (
                settings.openai_api_key 
                and model_name in self.openrouter_models
                and model_name.startswith("openai/")
            ):
                openai_model = self.openrouter_models[model_name]
                model = ChatOpenAI(
                    model=openai_model,
                    temperature=temperature,
                    streaming=streaming,
                    api_key=settings.openai_api_key,
                    **kwargs
                )
                return model
            else:
                raise ValueError(f"Failed to create model and no fallback available: {e}")
    
    def create_agent_chain(
        self,
        system_prompt: str,
        model_name: str = "google/gemini-2.5-flash", 
        temperature: float = 0.2,
        streaming: bool = False,
        **kwargs
    ):
        """
        Create a simple LangChain for an agent with system prompt
        
        Args:
            system_prompt: The system prompt for the agent
            model_name: The model to use
            temperature: The sampling temperature (0-1)
            streaming: Whether to enable response streaming
            **kwargs: Additional model parameters
            
        Returns:
            A LangChain chain with the specified model and prompt
        """
        model = self.get_model(
            model_name=model_name,
            temperature=temperature,
            streaming=streaming,
            **kwargs
        )
        
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt),
            MessagesPlaceholder(variable_name="messages"),
        ])
        
        return prompt | model


# Create a singleton instance
ai_provider = AIProvider()
