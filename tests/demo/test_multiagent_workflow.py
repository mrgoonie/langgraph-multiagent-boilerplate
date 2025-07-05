"""
Demonstration test of the complete multi-agent workflow.

This test demonstrates the workflow described in PROJECT_OVERVIEW.md:
1. User sends a message to a crew
2. Supervisor agent receives and analyzes input
3. Supervisor decides whether to answer directly or create a plan
4. If a plan is created, supervisor delegates tasks to agents
5. Agents execute their tasks
6. Supervisor gathers results and responds
7. All conversations are stored in the database

This test can run in two modes:
- API Mode: Uses real HTTP endpoints (requires API server running at localhost:8000)
- Direct Mode: Calls functions directly without HTTP (can run without API server)

Usage:
    # To run in API mode (default, requires server running)
    python tests/demo/test_multiagent_workflow.py
    
    # To run in direct mode (doesn't require server)
    python tests/demo/test_multiagent_workflow.py --direct
"""
import asyncio
import aiohttp
import json
import uuid
import time
import logging
from pprint import pprint
import sys
import os
import argparse
from typing import List, Dict, Any, Optional, Literal

# Add project root to path to allow importing app modules directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.langgraph.supervisor import SupervisorState, AgentState
from app.models.activity_log import ActivityType
from app.db.base import get_db
from app.services.conversation_service import ConversationService, ActivityLogService
from app.services.crew_service import CrewService, AgentService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("workflow-demo")

# API base URL
BASE_URL = "http://localhost:8000/api"

# Test configuration
# You can change these values to test different scenarios
TEST_USER_ID = "demo-workflow-user"
TEST_MESSAGE_SIMPLE = "What's the weather like today?"  # Simple query that supervisor might answer directly
TEST_MESSAGE_COMPLEX = "Research the impact of AI on healthcare and provide a detailed analysis with pros and cons."  # Complex query that needs planning
TEST_MESSAGE_TRAVEL = "I need travel advice for Nha Trang beach in Vietnam. What places should I visit and what local food should I try?"  # Travel advice example from PROJECT_OVERVIEW.md


async def create_test_crew():
    """Create a test crew with multiple agents for the demonstration"""
    logger.info("Creating a test crew with multiple agents")
    
    # Create a crew
    crew_url = f"{BASE_URL}/crews/"
    crew_payload = {
        "name": "Demo Workflow Crew",
        "description": "A crew created for demonstrating the multi-agent workflow",
        "metadata": {
            "purpose": "testing"
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(crew_url, json=crew_payload) as response:
            if response.status == 201:
                crew = await response.json()
                crew_id = crew["id"]
                logger.info(f"Created crew with ID: {crew_id}")
                
                # Create supervisor agent
                supervisor = await create_agent(session, crew_id, "Supervisor", True, 
                                              "You are the supervisor agent responsible for coordinating other agents.")
                
                # Create specialized agents
                researcher = await create_agent(session, crew_id, "Researcher", False,
                                             "You are a research agent specialized in gathering information.")
                
                analyst = await create_agent(session, crew_id, "Analyst", False,
                                          "You are an analyst agent specialized in analyzing data and drawing conclusions.")
                
                writer = await create_agent(session, crew_id, "Writer", False,
                                         "You are a writer agent specialized in creating well-written content.")
                
                return {
                    "crew_id": crew_id,
                    "supervisor": supervisor,
                    "agents": [researcher, analyst, writer]
                }
            else:
                error = await response.text()
                logger.error(f"Failed to create crew: {error}")
                raise Exception(f"Failed to create crew: {response.status}")


async def create_agent(session, crew_id, name, is_supervisor, system_prompt):
    """Create an agent for the crew"""
    agent_url = f"{BASE_URL}/crews/{crew_id}/agents"
    agent_payload = {
        "name": name,
        "description": f"Test {name} agent for workflow demonstration",
        "is_supervisor": is_supervisor,
        "system_prompt": system_prompt,
        "model": "google/gemini-1.5-pro",  # Use model of your choice
        "tools": []  # Add tools if needed
    }
    
    async with session.post(agent_url, json=agent_payload) as response:
        if response.status == 201:
            agent = await response.json()
            logger.info(f"Created agent: {name} (ID: {agent['id']})")
            return agent
        else:
            error = await response.text()
            logger.error(f"Failed to create agent {name}: {error}")
            raise Exception(f"Failed to create agent: {response.status}")


async def create_conversation(crew_id):
    """Create a test conversation for the demonstration"""
    logger.info("Creating a test conversation")
    
    url = f"{BASE_URL}/conversations/"
    payload = {
        "user_id": TEST_USER_ID,
        "crew_id": crew_id,
        "title": "Multi-Agent Workflow Demonstration"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status == 201:
                result = await response.json()
                conversation_id = result["id"]
                logger.info(f"Created conversation with ID: {conversation_id}")
                return conversation_id
            else:
                error = await response.text()
                logger.error(f"Failed to create conversation: {error}")
                raise Exception(f"Failed to create conversation: {response.status}")


async def test_chat_with_monitoring(conversation_id, message):
    """
    Test the chat endpoint with real-time monitoring of the multi-agent workflow.
    This simulates the user sending a message to the crew.
    """
    logger.info(f"Testing chat with message: '{message}'")
    
    url = f"{BASE_URL}/conversations/{conversation_id}/chat"
    payload = {"message": message}
    
    # Start time for tracking workflow duration
    start_time = time.time()
    logger.info("1. User sends message to crew via API")
    
    async with aiohttp.ClientSession() as session:
        # Send the chat request
        logger.info("2. Message sent to supervisor agent via API call")
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                result = await response.json()
                logger.info("9. Final response received from supervisor agent")
                
                # Calculate duration
                duration = time.time() - start_time
                
                logger.info(f"✓ Workflow completed in {duration:.2f} seconds")
                logger.info("Response content:")
                print("-" * 80)
                print(result["content"])
                print("-" * 80)
                
                # Now, fetch activity logs to analyze the workflow
                await analyze_workflow(conversation_id, start_time)
                
                return result
            else:
                error = await response.text()
                logger.error(f"Error: {response.status}, {error}")
                return None


async def analyze_workflow(conversation_id, start_time):
    """
    Analyze the workflow by fetching activity logs and messages from the database.
    This demonstrates how the workflow steps are recorded in the database.
    """
    logger.info("Analyzing workflow execution from database records")
    
    # Fetch activity logs related to this conversation
    url = f"{BASE_URL}/activity-logs/?conversation_id={conversation_id}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                logs = await response.json()
                
                # Process logs to demonstrate the workflow
                analyze_logs(logs, start_time)
                
                # Fetch messages to see the final conversation
                await fetch_conversation_messages(session, conversation_id)
            else:
                logger.error(f"Failed to fetch activity logs: {response.status}")


def analyze_logs(logs, start_time):
    """Process activity logs to visualize the workflow steps"""
    if not logs:
        logger.warning("No activity logs found for this conversation")
        return
    
    logger.info(f"Found {len(logs)} activity log entries for this conversation")
    
    # Organize logs by activity type to show the workflow phases
    planning_logs = [log for log in logs if log["description"] and "plan" in log["description"].lower()]
    task_logs = [log for log in logs if log["description"] and "task" in log["description"].lower()]
    message_logs = [log for log in logs if log["activity_type"] == "AGENT_MESSAGE"]
    
    # Display workflow statistics
    logger.info(f"Workflow statistics:")
    logger.info(f"- Planning actions: {len(planning_logs)}")
    logger.info(f"- Task assignments: {len(task_logs)}")
    logger.info(f"- Agent messages: {len(message_logs)}")
    
    # List activities in chronological order with relative timestamps
    logger.info("Workflow timeline:")
    for log in sorted(logs, key=lambda x: x["created_at"]):
        timestamp = time.strptime(log["created_at"], "%Y-%m-%dT%H:%M:%S.%f")
        relative_time = time.mktime(timestamp) - start_time
        agent_name = log.get("agent_name", "System")
        logger.info(f"  +{relative_time:.2f}s - {agent_name}: {log['description']}")


async def fetch_conversation_messages(session, conversation_id):
    """Fetch messages from the conversation to show the complete dialogue"""
    url = f"{BASE_URL}/conversations/{conversation_id}/messages"
    
    async with session.get(url) as response:
        if response.status == 200:
            messages = await response.json()
            
            logger.info(f"Conversation history ({len(messages)} messages):")
            for msg in messages:
                role = "User" if msg["role"] == "user" else "AI"
                content = msg["content"]
                # Truncate long messages for display
                if len(content) > 100:
                    content = content[:97] + "..."
                logger.info(f"  {role}: {content}")
        else:
            logger.error(f"Failed to fetch conversation messages: {response.status}")


async def test_streaming_chat(conversation_id, message):
    """Test the streaming chat endpoint with a complex query"""
    logger.info(f"Testing streaming chat with message: '{message}'")
    
    url = f"{BASE_URL}/conversations/{conversation_id}/chat/stream"
    payload = {"message": message}
    
    start_time = time.time()
    logger.info("1. User sends streaming message to crew via API")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                logger.info("2. Streaming connection established")
                
                # Process the streaming response
                content_so_far = ""
                async for chunk in response.content:
                    chunk_data = chunk.decode('utf-8')
                    if chunk_data.startswith('data:') and 'content' in chunk_data:
                        try:
                            # Parse the SSE data format
                            data_str = chunk_data.replace('data: ', '', 1).strip()
                            if data_str and data_str != '[DONE]':
                                data = json.loads(data_str)
                                if 'choices' in data and data['choices'][0].get('delta', {}).get('content'):
                                    content = data['choices'][0]['delta']['content']
                                    content_so_far += content
                                    # Print without newline to show streaming effect
                                    print(content, end='', flush=True)
                        except json.JSONDecodeError:
                            pass
                
                print()  # Add newline after streaming completes
                duration = time.time() - start_time
                logger.info(f"✓ Streaming workflow completed in {duration:.2f} seconds")
                
                # Analyze workflow after stream completes
                await analyze_workflow(conversation_id, start_time)
                
                return content_so_far
            else:
                error = await response.text()
                logger.error(f"Error: {response.status}, {error}")
                return None


async def main_api_mode():
    """Run the multi-agent workflow demonstration using API endpoints"""
    logger.info("=== Starting Multi-Agent Workflow Demonstration (API Mode) ===")
    
    try:
        # Create a test crew with multiple agents
        crew = await create_test_crew()
        crew_id = crew["crew_id"]
        
        # Create a conversation
        conversation_id = await create_conversation(crew_id)
        
        # Test with a simple query (likely to be answered directly)
        logger.info("\n=== Testing Simple Query Workflow ===")
        await test_chat_with_monitoring(conversation_id, TEST_MESSAGE_SIMPLE)
        
        # Wait a bit between tests
        await asyncio.sleep(2)
        
        # Test with a complex query (likely to require planning and agent delegation)
        logger.info("\n=== Testing Complex Query Workflow ===")
        await test_streaming_chat(conversation_id, TEST_MESSAGE_COMPLEX)
        
        logger.info("\n=== Multi-Agent Workflow Demonstration Completed ===")
        
    except Exception as e:
        logger.error(f"Error in workflow demonstration (API mode): {str(e)}", exc_info=True)


async def test_direct_workflow(supervisor_func, conversation_id, message):
    """Test the supervisor workflow directly without using HTTP endpoints"""
    from langchain_core.messages import HumanMessage, AIMessage
    from app.core.langgraph.supervisor import SupervisorState

    logger.info(f"Testing direct workflow with message: '{message}'")
    start_time = time.time()
    
    # Initialize the supervisor state
    state = {
        "messages": [],
        "user_input": message,
        "plan": None,
        "agents": {},
        "crew_id": "test-crew-id",
        "conversation_id": conversation_id
    }
    
    # Log the workflow steps
    logger.info("1. User input received directly by supervisor")
    
    # Execute the mock supervisor workflow
    logger.info("2-8. Executing the supervisor workflow")
    result = await supervisor_func(state)
    
    # Calculate duration
    duration = time.time() - start_time
    logger.info(f"9. Workflow completed in {duration:.2f} seconds")
    
    # Display the final response
    if result and result.get("messages") and len(result["messages"]) > 0:
        final_message = result["messages"][-1]
        logger.info("Final response:")
        print("-" * 80)
        print(final_message.content if hasattr(final_message, 'content') else final_message)
        print("-" * 80)
    else:
        logger.warning("No response generated from workflow")
    
    # Analyze the workflow execution
    analyze_direct_workflow(result, start_time)
    
    return result


def analyze_direct_workflow(result, start_time):
    """Analyze the workflow execution results from direct function calls"""
    logger.info("Analyzing direct workflow execution:")
    
    if not result:
        logger.warning("No result to analyze")
        return
    
    # Check if a plan was created
    if result.get("plan"):
        logger.info("✓ Supervisor created a plan")
        plan = result["plan"]
        logger.info(f"Plan details: {plan}")
    else:
        logger.info("✓ Supervisor answered directly (no plan created)")
    
    # Check agent states
    if result.get("agents"):
        logger.info(f"Agent activity summary:")
        for agent_id, agent_state in result["agents"].items():
            status = agent_state.get("status", "unknown")
            agent_name = agent_state.get("agent_name", agent_id)
            logger.info(f"  - {agent_name}: {status}")
            
            if agent_state.get("results"):
                logger.info(f"    Results: {agent_state['results']}")
    
    # Check messages history
    if result.get("messages"):
        message_count = len(result["messages"])
        logger.info(f"✓ Conversation has {message_count} messages in history")
    
    # Show timing information
    end_time = time.time()
    logger.info(f"Total analysis time: {end_time - start_time:.2f} seconds")



async def main_direct_mode():
    """Run the multi-agent workflow demonstration using direct function calls"""
    logger.info("=== Starting Multi-Agent Workflow Demonstration (Direct Mode) ===")
    
    try:
        # Import modules needed for direct mode
        from langchain_core.messages import HumanMessage, AIMessage
        from app.core.langgraph.supervisor import SupervisorState, AgentState
        import uuid
        
        # Create test agents configuration
        agents = [
            {
                "id": str(uuid.uuid4()),
                "name": "Researcher",
                "tools": [{"type": "search", "name": "web_search"}]
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Analyst",
                "tools": [{"type": "calculator", "name": "math_tool"}]
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Writer",
                "tools": [{"type": "text_processor", "name": "text_formatter"}]
            }
        ]
        
        # Generate a test crew ID and conversation ID
        test_crew_id = str(uuid.uuid4())
        conversation_id = str(uuid.uuid4())
        
        # Instead of trying to create a real supervisor graph (which is complex and requires
        # LangGraph setup), we'll create a simplified mock of the supervisor workflow
        logger.info("Creating simplified mock supervisor workflow")
        
        # Create a mock supervisor function that simulates the workflow
        async def mock_supervisor_workflow(state):
            """Mock implementation of supervisor workflow for demonstration"""
            # Extract the user input from state
            user_input = state.get("user_input", "")
            logger.info(f"Processing input: {user_input}")
            
            # Initialize agent states
            agent_states = {}
            for agent in agents:
                agent_id = agent["id"]
                agent_states[agent_id] = {
                    "agent_id": agent_id,
                    "agent_name": agent["name"],
                    "messages": [],
                    "status": "idle",
                    "results": None,
                    "tools": agent.get("tools", [])
                }
            
            # Simulate workflow steps based on input complexity
            result = state.copy()
            result["agents"] = agent_states
            
            # Step 1: Analyze input (decide if simple or complex)
            logger.info("2. Supervisor analyzing input")
            
            # Simulate supervisor decision making
            if any(word in user_input.lower() for word in ["simple", "weather", "hello", "hi"]):
                # For simple queries, answer directly
                logger.info("3. Supervisor decided to answer directly (simple query)")
                await asyncio.sleep(1)  # Simulate AI thinking time
                
                if "weather" in user_input.lower():
                    response = "Based on my capabilities, I don't have access to real-time weather data. To get accurate weather information for today, I recommend checking a weather service like weather.com, AccuWeather, or using a weather app on your device. If you're interested in weather forecasts or historical weather patterns for a specific location, I'd be happy to help research that with my agent team."
                elif "hello" in user_input.lower() or "hi" in user_input.lower():
                    response = "Hello! I'm your AI assistant crew supervisor. How can I help you today? I can answer questions, research topics, analyze data, or help you with various tasks."
                else:
                    response = f"I understand you're asking about '{user_input}'. This is a straightforward question that I can answer directly without needing to coordinate with other specialized agents in my crew."
            
            # Special case for Nha Trang travel advice (from PROJECT_OVERVIEW.md example)
            elif "nha trang" in user_input.lower() and ("travel" in user_input.lower() or "beach" in user_input.lower() or "vietnam" in user_input.lower() or "food" in user_input.lower()):
                logger.info("3. Supervisor decided to create a plan (travel advice query)")
                
                # Simulate plan creation specifically for travel advice
                await asyncio.sleep(1)  # Simulate AI thinking time
                
                # Create a specialized plan for travel advice
                plan = {
                    "steps": [
                        {"agent": "Researcher", "task": "Search for tourist attractions and places to visit in Nha Trang beach, Vietnam"},
                        {"agent": "Analyst", "task": "Search for local food and culinary experiences in Nha Trang, Vietnam"},
                        {"agent": "Writer", "task": "Create a comprehensive travel guide for Nha Trang beach combining attractions and food recommendations"}
                    ],
                    "goal": "Provide comprehensive travel advice for Nha Trang beach in Vietnam"
                }
                result["plan"] = plan
                logger.info("4. Supervisor created a detailed travel advice plan")
                
                # Assign tasks to agents
                logger.info("5. Supervisor delegating tasks to travel research agents")
                for agent_id, agent_state in result["agents"].items():
                    agent_name = agent_state["agent_name"]
                    # Find tasks for this agent
                    agent_tasks = [step for step in plan["steps"] if step["agent"] == agent_name]
                    if agent_tasks:
                        agent_state["status"] = "working"
                
                # Simulate agents working on travel research
                logger.info("6. Agents executing their travel research tasks using Search API MCP server")
                await asyncio.sleep(2)  # Simulate agent work time
                
                # Update agent results with realistic travel advice content
                for agent_id, agent_state in result["agents"].items():
                    if agent_state["status"] == "working":
                        agent_name = agent_state["agent_name"]
                        agent_state["status"] = "complete"
                        
                        # Generate specific content based on agent role
                        if agent_name == "Researcher":
                            agent_state["results"] = "After searching for tourist attractions in Nha Trang, I found these top places to visit: 1) Vinpearl Land Amusement Park - accessible via the world's longest over-sea cable car, 2) Hon Mun Island - perfect for snorkeling and diving with vibrant coral reefs, 3) Po Nagar Cham Towers - ancient Hindu temples from the 8th century, 4) Long Son Pagoda with its giant white Buddha statue, 5) Tran Phu Beach - the main beach with clear waters and various water sports. Most attractions are accessible via taxi or motorbike rental."
                        elif agent_name == "Analyst":
                            agent_state["results"] = "My research on Nha Trang's culinary scene reveals these must-try dishes: 1) Bánh căn - small savory rice pancakes topped with seafood or meat, 2) Bún cá - fish noodle soup with local herbs, 3) Nem nướng Ninh Hòa - grilled pork rolls served with rice paper and herbs, 4) Fresh seafood at Thap Ba area - try the grilled scallops with peanuts and scallions, 5) Bánh xèo mực - squid pancakes. Best food areas include Thap Ba Street, Dam Market, and the Night Market near Tran Phu Beach."
                        elif agent_name == "Writer":
                            agent_state["results"] = "Based on our research, I recommend a 3-day itinerary for Nha Trang: Day 1: Start at Tran Phu Beach, visit Po Nagar Cham Towers, then enjoy seafood at Thap Ba Street. Day 2: Take the cable car to Vinpearl Land for a day of fun, return to try nem nướng Ninh Hòa for dinner. Day 3: Book a boat tour to Hon Mun Island for snorkeling, visit Long Son Pagoda in the afternoon, and end with bánh căn at the Night Market. The best time to visit is between March and September to avoid the rainy season. For transportation, motorbike rentals cost around 150,000 VND/day, while taxis are plentiful but negotiate prices beforehand."
                
                logger.info("7. Supervisor gathering travel advice results")
                
                # Simulate supervisor combining travel advice results
                logger.info("8. Supervisor creating final travel advice response")
                await asyncio.sleep(1)  # Simulate AI combining time
                
                # Create comprehensive travel guide for Nha Trang
                researcher_result = ""
                analyst_result = ""
                writer_result = ""
                
                # Safely extract results by agent name instead of using hardcoded indices
                for agent_id, agent_state in result["agents"].items():
                    if agent_state["agent_name"] == "Researcher":
                        researcher_result = agent_state.get("results", "")
                    elif agent_state["agent_name"] == "Analyst":
                        analyst_result = agent_state.get("results", "")
                    elif agent_state["agent_name"] == "Writer":
                        writer_result = agent_state.get("results", "")
                
                response = f"# Nha Trang Beach Travel Guide\n\n## Places to Visit\n{researcher_result}\n\n## Local Food to Try\n{analyst_result}\n\n## Recommended Itinerary\n{writer_result}\n\nI hope this helps with your trip to Nha Trang! Let me know if you need any specific details about accommodations, transportation, or have other questions about your visit to Vietnam."
            
            # Default case for other complex queries
            else:
                # For complex queries, create a plan
                logger.info("3. Supervisor decided to create a plan (complex query)")
                
                # Simulate plan creation
                await asyncio.sleep(1)  # Simulate AI thinking time
                
                # Create a mock plan
                plan = {
                    "steps": [
                        {"agent": "Researcher", "task": f"Research information about: {user_input}"},
                        {"agent": "Analyst", "task": f"Analyze findings related to: {user_input}"},
                        {"agent": "Writer", "task": f"Create a comprehensive response about: {user_input}"}
                    ],
                    "goal": f"Answer the user's question about: {user_input}"
                }
                result["plan"] = plan
                logger.info("4. Supervisor created a detailed plan")
                
                # Assign tasks to agents
                logger.info("5. Supervisor delegating tasks to agents")
                for agent_id, agent_state in result["agents"].items():
                    agent_name = agent_state["agent_name"]
                    # Find tasks for this agent
                    agent_tasks = [step for step in plan["steps"] if step["agent"] == agent_name]
                    if agent_tasks:
                        agent_state["status"] = "working"
                
                # Simulate agents working
                logger.info("6. Agents executing their tasks")
                await asyncio.sleep(2)  # Simulate agent work time
                
                # Generate more meaningful results for the AI healthcare example
                if "ai" in user_input.lower() and "healthcare" in user_input.lower():
                    # Update agent results with realistic healthcare AI content
                    for agent_id, agent_state in result["agents"].items():
                        if agent_state["status"] == "working":
                            agent_name = agent_state["agent_name"]
                            agent_state["status"] = "complete"
                            
                            # Generate specific content based on agent role
                            if agent_name == "Researcher":
                                agent_state["results"] = "Research findings on AI in healthcare: 1) AI applications include diagnostic tools, predictive analytics, virtual nursing assistants, drug discovery, and personalized medicine. 2) Major implementations: IBM Watson for oncology, Google DeepMind's AlphaFold for protein folding, and Babylon Health's symptom checker. 3) Market projected to grow from $11 billion in 2021 to over $187 billion by 2030. 4) Most advanced areas include radiology, pathology, and dermatology where AI can often match or exceed human performance in specific diagnostic tasks."
                            elif agent_name == "Analyst":
                                agent_state["results"] = "Analysis of AI in healthcare - PROS: 1) Improved diagnostic accuracy (studies show 5-15% improvement in early detection of diseases like cancer), 2) Reduced healthcare costs (estimated 10-15% savings through efficiency), 3) Better patient outcomes through personalized treatment plans, 4) Alleviation of healthcare worker shortages, 5) Faster drug development (reduced by 1-2 years). CONS: 1) Data privacy and security concerns, 2) Regulatory challenges, 3) Risk of algorithmic bias affecting marginalized communities, 4) High implementation costs, 5) Potential reduction in human judgment and care elements."
                            elif agent_name == "Writer":
                                agent_state["results"] = "The impact of AI on healthcare represents a transformative shift in medical practice. While offering remarkable benefits like enhanced diagnostic capabilities and personalized treatment approaches, it also presents significant ethical and implementation challenges. The key to successful AI integration lies in balancing technological advancement with human-centered care, ensuring proper regulatory oversight, addressing equity concerns, and maintaining patient privacy. Healthcare institutions should adopt a strategic approach to AI implementation, focusing on areas with proven benefits while continuously evaluating outcomes and addressing emerging issues."
                else:
                    # For other complex queries, provide generic but useful responses
                    for agent_id, agent_state in result["agents"].items():
                        if agent_state["status"] == "working":
                            agent_name = agent_state["agent_name"]
                            agent_state["status"] = "complete"
                            agent_state["results"] = f"{agent_name}'s analysis on '{user_input}' would contain factual information, insights, and recommendations based on the latest available data."
                
                logger.info("7. Supervisor gathering agent results")
                
                # Simulate supervisor combining results
                logger.info("8. Supervisor creating final response")
                await asyncio.sleep(1)  # Simulate AI combining time
                
                # Create combined response based on the query type
                if "ai" in user_input.lower() and "healthcare" in user_input.lower():
                    researcher_result = ""
                    analyst_result = ""
                    writer_result = ""
                    
                    # Safely extract results by agent name instead of using hardcoded indices
                    for agent_id, agent_state in result["agents"].items():
                        if agent_state["agent_name"] == "Researcher":
                            researcher_result = agent_state.get("results", "")
                        elif agent_state["agent_name"] == "Analyst":
                            analyst_result = agent_state.get("results", "")
                        elif agent_state["agent_name"] == "Writer":
                            writer_result = agent_state.get("results", "")
                    
                    response = f"# The Impact of AI on Healthcare\n\n## Research Overview\n{researcher_result}\n\n## Analysis of Pros and Cons\n{analyst_result}\n\n## Conclusion\n{writer_result}\n\nThis analysis provides a balanced view of AI's current and potential impact on healthcare. Would you like me to explore any specific aspect of this topic in more detail?"
                else:
                    # Generic response for other topics
                    combined_results = ""
                    for agent_id, agent_state in result["agents"].items():
                        if agent_state["results"]:
                            combined_results += f"\n- {agent_state['agent_name']}: {agent_state['results']}"
                    
                    response = f"Based on our analysis of '{user_input}', here are the findings:{combined_results}\n\nConclusion: This comprehensive response integrates research, analysis, and synthesis from multiple specialized agents to address your query in detail."
            
            # Update the messages in the state
            messages = result.get("messages", [])
            messages.append(HumanMessage(content=user_input))
            messages.append(AIMessage(content=response))
            result["messages"] = messages
            
            return result
        
        # Run the simple query workflow
        logger.info("\n=== Testing Simple Query Workflow (Direct Mode) ===")
        await test_direct_workflow(mock_supervisor_workflow, conversation_id, TEST_MESSAGE_SIMPLE)
        
        # Wait a bit between tests
        await asyncio.sleep(2)
        
        # Run the complex query workflow
        logger.info("\n=== Testing Complex Query Workflow (Direct Mode) ===")
        await test_direct_workflow(mock_supervisor_workflow, conversation_id, TEST_MESSAGE_COMPLEX)
        
        # Wait a bit between tests
        await asyncio.sleep(2)
        
        # Run the travel advice workflow (Nha Trang example from PROJECT_OVERVIEW.md)
        logger.info("\n=== Testing Travel Advice Workflow (Direct Mode) ===")
        await test_direct_workflow(mock_supervisor_workflow, conversation_id, TEST_MESSAGE_TRAVEL)
        
        logger.info("\n=== Multi-Agent Workflow Demonstration Completed ===")
        
    except Exception as e:
        logger.error(f"Error in workflow demonstration (Direct mode): {str(e)}", exc_info=True)


async def main():
    """Parse command line arguments and run the appropriate mode"""
    parser = argparse.ArgumentParser(
        description="Multi-Agent Workflow Demonstration"
    )
    parser.add_argument(
        "--direct", 
        action="store_true", 
        help="Run in direct function call mode (no API server required)"
    )
    args = parser.parse_args()
    
    if args.direct:
        await main_direct_mode()
    else:
        await main_api_mode()


if __name__ == "__main__":
    asyncio.run(main())
