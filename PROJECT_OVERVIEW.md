# LangGraph Multi-Agent Boilerplate

A robust boilerplate for building AI agent clusters with LangGraph, featuring a supervisor architecture, MCP server integration, and comprehensive APIs.

## Project Overview

This project provides a boilerplate for developers who want to start building AI agent clusters efficiently. The system is built on LangGraph and follows a supervisor architecture where multiple AI agents work together under the coordination of a supervisor agent.

### Core Concepts

- **Multi-agent System (Supervisor Architecture)**
  - Each AI agent cluster can have multiple AI agent crews (AI Crews)
  - Each AI crew can have multiple AI agents, led by a supervisor (a default AI agent of an AI crew)
  - Each AI agent can call tools of attached MCP servers

### How It Works

1. An AI crew contains many AI agents, led by a supervisor agent
2. These AI agents communicate with each other to accomplish goals
3. When a user chats with a crew, the supervisor agent receives the input via API call
4. The supervisor analyzes the input prompt and the crew's capabilities (AI agents underneath and their tools from attached MCP servers)
5. The supervisor decides whether to answer instantly or create a detailed plan for the AI agents to follow
6. If a plan is created, it requests the AI agents to perform tasks
7. The supervisor waits for all AI agents to finish given tasks, ensuring the process doesn't hang too long
8. The supervisor gathers all results, analyzes them, and responds to the user based on the original input prompt
9. All conversations are managed in the database

## Project Structure

```
.
├── app
│   ├── api
│   │   ├── exceptions.py           # Custom exceptions and error handling
│   │   ├── middleware              # Security and auth middleware
│   │   └── routes                  # API route definitions
│   ├── core
│   │   ├── config.py               # Application configuration
│   │   └── langgraph              # LangGraph core components
│   ├── db
│   │   └── base.py                # Database connection and session management
│   ├── main.py                    # FastAPI application entry point
│   ├── models
│   │   ├── activity_log.py        # Activity logging models
│   │   ├── conversation.py        # Conversation and message models
│   │   └── crew.py                # Crew, Agent, MCPServer models
│   ├── schemas                    # Pydantic schemas for validation
│   └── services                   # Business logic services
│       ├── ai_provider.py         # AI model provider service
│       ├── conversation_service.py # Conversation management
│       ├── crew_service.py        # Crew and agent management
│       ├── mcp_service.py         # MCP server integration
│       └── storage_service.py     # Cloudflare R2 storage integration
├── tests                          # Test suite
├── .env.example                   # Environment variables template
├── pyproject.toml                 # Project metadata and configuration
├── requirements.txt               # Python dependencies
└── PROJECT_OVERVIEW.md            # This file
```

## Features

- **Core Features**
  - Create & manage AI crews (with supervisor agent, add/remove agents)
  - Create & manage AI agents (add/remove MCP tools, custom system prompts, custom AI models)
  - Create & manage MCP servers (supports Streamable HTTP transport via `langchain-mcp-adapters`)
  - Create & manage user conversations with AI crews
  - Monitor activity logs of AI crews and AI agents
  - API for frontend interaction with streaming support
  - Swagger API documentation

- **Technical Features**
  - Python-based with FastAPI for the API layer
  - LangGraph for multi-agent orchestration
  - PostgreSQL database with UUID primary keys
  - Cloudflare R2 for cloud storage
  - Model Context Protocol (MCP) server integration
  - Streaming API responses
  - Comprehensive error handling and security best practices
  - Extensive test coverage

## API Routes

- **Crews and Agents**
  - `GET /api/crews` - Get all crews
  - `POST /api/crews` - Create a new crew
  - `GET /api/crews/{crew_id}` - Get a specific crew
  - `PUT /api/crews/{crew_id}` - Update a crew
  - `DELETE /api/crews/{crew_id}` - Delete a crew
  - `GET /api/agents` - Get all agents
  - `POST /api/agents` - Create a new agent
  - `GET /api/agents/{agent_id}` - Get a specific agent
  - `PUT /api/agents/{agent_id}` - Update an agent
  - `DELETE /api/agents/{agent_id}` - Delete an agent
  - `POST /api/agents/{agent_id}/tools/{tool_id}` - Assign a tool to an agent
  - `DELETE /api/agents/{agent_id}/tools/{tool_id}` - Remove a tool from an agent

- **MCP Servers and Tools**
  - `GET /api/mcp-servers` - Get all MCP servers
  - `POST /api/mcp-servers` - Create a new MCP server
  - `GET /api/mcp-servers/{server_id}` - Get a specific MCP server
  - `PUT /api/mcp-servers/{server_id}` - Update an MCP server
  - `DELETE /api/mcp-servers/{server_id}` - Delete an MCP server
  - `GET /api/mcp-servers/{server_id}/tools` - Get tools for an MCP server
  - `POST /api/mcp-servers/{server_id}/tools` - Add a tool to an MCP server
  - `DELETE /api/mcp-servers/{server_id}/tools/{tool_id}` - Remove a tool from an MCP server

- **Conversations and Chat**
  - `GET /api/conversations` - Get all conversations
  - `POST /api/conversations` - Create a new conversation
  - `GET /api/conversations/{conversation_id}` - Get a specific conversation
  - `PUT /api/conversations/{conversation_id}` - Update a conversation
  - `DELETE /api/conversations/{conversation_id}` - Delete a conversation
  - `GET /api/conversations/{conversation_id}/messages` - Get messages for a conversation
  - `POST /api/conversations/{conversation_id}/messages` - Add a message to a conversation
  - `POST /api/conversations/{conversation_id}/chat` - Send a message to the crew and get a response
  - `POST /api/conversations/{conversation_id}/chat/stream` - Send a message and get a streaming response

- **Storage**
  - `POST /api/storage/upload` - Upload a file to cloud storage
  - `GET /api/storage/files/{key}` - Download a file from storage
  - `GET /api/storage/urls/{key}` - Get a presigned URL for a file
  - `DELETE /api/storage/files/{key}` - Delete a file from storage
  - `GET /api/storage/files` - List files in storage

- **Health Check**
  - `GET /api/health` - Check API health

## Dependencies

- **Core**
  - Python 3.10+
  - FastAPI
  - LangGraph
  - LangChain
  - SQLAlchemy (async)
  - Pydantic
  - Alembic (for migrations)
  - OpenRouter AI API

- **Storage**
  - PostgreSQL
  - Cloudflare R2 (via boto3)

- **Testing**
  - Pytest
  - TestClient

- **Utilities**
  - python-dotenv
  - uvicorn
  - httpx
  - tenacity

## Getting Started

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd langgraph-multiagent-boilerplate
   ```

2. **Set up environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Run the application**
   ```bash
   uvicorn app.main:app --reload
   ```

5. **Access the API documentation**
   - Swagger UI: http://localhost:8000/api/docs
   - ReDoc: http://localhost:8000/api/redoc

## Changelog

- **2023-07-03**: Initial implementation
  - Set up project structure and dependencies
  - Implemented core models and relationships
  - Added AI provider service with OpenRouter integration
  - Implemented MCP server integration with `langchain-mcp-adapters`
  - Created API routes for crews, agents, conversations, and storage
  - Added streaming support for chat interactions
  - Implemented error handling and security best practices
  - Added test scaffolding for core services
