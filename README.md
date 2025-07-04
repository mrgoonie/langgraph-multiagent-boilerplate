# LangGraph Multi-Agent Boilerplate

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)

A robust boilerplate for building AI agent clusters efficiently using LangGraph with supervisor architecture, Model Context Protocol (MCP) integration, and comprehensive API.

## 🌟 Features

- **Multi-Agent Architecture**: Build AI agent clusters with supervisor coordination
- **LangGraph Integration**: Leverage LangGraph's powerful state management for agent workflows
- **MCP Support**: Integrate tools via Model Context Protocol servers
- **Streaming API**: Real-time streaming responses for interactive conversations
- **Database Persistence**: Store conversations, agent states, and activity logs in PostgreSQL
- **Cloud Storage**: File management with Cloudflare R2
- **Comprehensive API**: RESTful endpoints with FastAPI, including Swagger documentation
- **Security**: Authentication middleware, error handling, and security best practices

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL
- Cloudflare R2 account (optional, for cloud storage)
- OpenRouter AI API key (or other compatible AI provider)

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/langgraph-multiagent-boilerplate.git
cd langgraph-multiagent-boilerplate
```

2. **Set up a Python virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure environment variables**

```bash
cp .env.example .env
# Edit .env with your settings (database, API keys, etc.)
```

5. **Set up the database**

```bash
# Create a PostgreSQL database
# Then run migrations (once implemented)
```

6. **Run the server**

```bash
uvicorn app.main:app --reload
```

7. **Access the API documentation**

- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## 📋 Project Structure

```
langgraph-multiagent-boilerplate/
├── app/
│   ├── api/
│   │   ├── exceptions.py       # Error handling
│   │   ├── middleware/         # Security & auth middleware
│   │   └── routes/             # API endpoints
│   ├── core/
│   │   ├── config.py           # Configuration management
│   │   └── langgraph/          # LangGraph components
│   ├── db/
│   │   └── base.py             # Database setup
│   ├── models/                 # SQLAlchemy models
│   ├── schemas/                # Pydantic schemas
│   ├── services/               # Business logic
│   └── main.py                 # Application entry point
├── tests/                      # Test suite
├── .env.example                # Environment template
├── pyproject.toml             # Python project metadata
├── requirements.txt           # Dependencies
├── README.md                  # This file
├── PROJECT_OVERVIEW.md        # Detailed project documentation
└── IMPLEMENTATION_TASKS.md    # Development roadmap
```

## 🧠 How It Works

### Multi-Agent System Architecture

1. **AI Crews**: Each AI agent cluster contains multiple crews, each led by a supervisor agent
2. **Supervisor Architecture**: The supervisor agent analyzes user input, creates plans, and assigns tasks to other agents
3. **Tool Integration**: Agents can access external tools via MCP servers
4. **Streaming Communication**: Real-time responses with event streaming
5. **Persistence**: All conversations, states, and activities are stored in the database

### Example Flow

1. User sends a message to a crew
2. Supervisor agent receives the input via API call
3. Supervisor analyzes the input and the crew's capabilities
4. Supervisor either answers directly or creates a detailed plan
5. If needed, supervisor assigns tasks to specialized agents
6. Agents perform their tasks using attached MCP tools
7. Supervisor collects results, analyzes them, and formulates a response
8. Response is streamed back to the user

## 🔌 API Reference

### Core Endpoints

#### Crews and Agents

- `GET /api/crews` - List all crews
- `POST /api/crews` - Create a new crew
- `GET /api/crews/{crew_id}` - Get crew details
- `PUT /api/crews/{crew_id}` - Update a crew
- `DELETE /api/crews/{crew_id}` - Delete a crew

- `GET /api/agents` - List all agents
- `POST /api/agents` - Create a new agent
- `GET /api/agents/{agent_id}` - Get agent details
- `PUT /api/agents/{agent_id}` - Update an agent
- `DELETE /api/agents/{agent_id}` - Delete an agent

#### Conversations

- `GET /api/conversations` - List conversations
- `POST /api/conversations` - Create a new conversation
- `GET /api/conversations/{conversation_id}` - Get conversation details
- `POST /api/conversations/{conversation_id}/chat` - Send a message and get a response
- `POST /api/conversations/{conversation_id}/chat/stream` - Get streaming response

See the Swagger documentation for the complete API reference.

## 📝 Usage Examples

### Creating a Crew with Agents

```python
import httpx

# Create a new crew
crew_data = {
    "name": "Research Crew",
    "description": "A crew specialized in research tasks",
    "metadata": {"specialization": "research"}
}

response = httpx.post("http://localhost:8000/api/crews", json=crew_data)
crew = response.json()
crew_id = crew["id"]

# Create a supervisor agent
supervisor_data = {
    "crew_id": crew_id,
    "name": "Research Supervisor",
    "description": "Supervises research operations",
    "system_prompt": "You are a research supervisor responsible for coordinating research efforts.",
    "model": "google/gemini-2.5-flash",
    "is_supervisor": True,
    "metadata": {}
}

httpx.post("http://localhost:8000/api/agents", json=supervisor_data)

# Create specialized agents
web_researcher_data = {
    "crew_id": crew_id,
    "name": "Web Researcher",
    "description": "Specializes in web research",
    "system_prompt": "You are a web researcher that finds accurate information online.",
    "model": "claude-3-sonnet",
    "is_supervisor": False,
    "metadata": {"specialty": "web_search"}
}

httpx.post("http://localhost:8000/api/agents", json=web_researcher_data)
```

### Starting a Conversation

```python
# Create a conversation with a crew
conversation_data = {
    "user_id": "user123",
    "crew_id": crew_id,
    "title": "Research on AI trends"
}

response = httpx.post("http://localhost:8000/api/conversations", json=conversation_data)
conversation = response.json()
conversation_id = conversation["id"]

# Send a message to the crew
message_data = {
    "message": "What are the latest trends in multi-agent AI systems?",
    "metadata": {}
}

# For non-streaming response
response = httpx.post(
    f"http://localhost:8000/api/conversations/{conversation_id}/chat", 
    json=message_data
)
print(response.json()["content"])

# For streaming response
with httpx.stream(
    "POST",
    f"http://localhost:8000/api/conversations/{conversation_id}/chat/stream",
    json=message_data,
    timeout=60.0
) as response:
    for chunk in response.iter_lines():
        if chunk.startswith("data: "):
            data = json.loads(chunk[6:])
            if "choices" in data and data["choices"][0]["delta"].get("content"):
                print(data["choices"][0]["delta"]["content"], end="")
```

## 🧪 Testing

Run the test suite with:

```bash
pytest
```

## 🔧 Configuration

Key environment variables:

- `DATABASE_URL`: PostgreSQL connection string
- `OPENROUTER_API_KEY`: OpenRouter API key
- `MCP_SERVER_URL`: URL of the MCP server
- `R2_ENDPOINT`, `R2_BUCKET_NAME`, etc.: Cloudflare R2 configuration
- `JWT_SECRET_KEY`: Secret for JWT authentication
- `DEBUG`: Enable debug mode

See `.env.example` for a complete list of configuration options.

## 🧩 Extending the Boilerplate

### Adding New MCP Tools

1. Register a new MCP server in the database
2. Discover and register tools from the server
3. Assign tools to agents

### Creating Custom Agent Types

1. Create a new agent with specialized system prompt
2. Assign relevant MCP tools to the agent
3. Add the agent to a crew

### Implementing Custom Workflows

1. Modify the supervisor logic in `app/core/langgraph/supervisor.py`
2. Adjust the state graph to implement your custom workflow

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📚 Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Model Context Protocol](https://langchain-ai.github.io/langgraph/agents/mcp/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
