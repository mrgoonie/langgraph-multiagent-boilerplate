"""
LangGraph supervisor architecture implementation

This module implements the core supervisor pattern for multi-agent coordination using
LangGraph's StateGraph for flexible workflow orchestration.
"""
import os
import json
import uuid
import asyncio
from typing import Dict, List, Literal, Optional, TypedDict, Any, Callable, Tuple
import uuid
from enum import Enum, auto
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langgraph.graph import StateGraph, END

from app.services.ai_provider import ai_provider
from app.models.crew import Agent, AgentTool, Crew, MCPTool


# Define types for our graph state
class AgentState(TypedDict):
    """State maintained for each agent in the system"""
    agent_id: str
    agent_name: str
    messages: List[BaseMessage]
    status: Literal["idle", "working", "complete", "error"]
    results: Optional[Dict[str, Any]]
    tools: List[Dict[str, Any]]


class SupervisorState(TypedDict):
    """The state maintained by the supervisor"""
    messages: List[BaseMessage]  # Chat history
    user_input: Optional[str]    # Current user input
    plan: Optional[Dict[str, Any]]  # The current execution plan
    agents: Dict[str, AgentState]  # States of all agents
    crew_id: str  # ID of the current crew
    conversation_id: str  # ID of the current conversation


# Define the supervisor actions enum
class SupervisorAction(str, Enum):
    """Actions that the supervisor can take"""
    ANSWER_DIRECTLY = "answer_directly"
    CREATE_PLAN = "create_plan"
    ASSIGN_TASKS = "assign_tasks"
    CHECK_STATUS = "check_status"
    COMBINE_RESULTS = "combine_results"
# Define the core supervisor functions
def analyze_input(state: SupervisorState) -> Dict[str, Any]:
    """
    Analyze the user input and decide if the supervisor can answer directly
    or needs to create a plan for agents
    """
    # Extract the user input and crew ID
    user_input = state["user_input"]
    crew_id = state["crew_id"]
    conversation_id = state["conversation_id"]
    agents = state["agents"]
    
    # If no user input provided, just return the current state
    if not user_input:
        return state
    
    # Get the AI model to use
    model = get_model("gpt-4-turbo")
    
    # Set up the system prompt
    system_prompt = """
    You are a Supervisor AI responsible for analyzing user inputs and deciding how to respond.
    
    Based on the user's input, decide if:
    1. You can answer directly (for simple questions, greetings, etc.) - respond with ACTION: ANSWER_DIRECTLY
    2. You need to create a plan involving multiple agents - respond with ACTION: CREATE_PLAN
    
    Only output your decision without explanation.
    """
    
    # Build the message list
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_input)
    ]
    
    # Get the AI model's response
    response = model.invoke(messages)
    
    # Extract the action from the response
    action = SupervisorAction.CREATE_PLAN  # Default
    if "ACTION: ANSWER_DIRECTLY" in response.content.upper():
        action = SupervisorAction.ANSWER_DIRECTLY
    
    # Update the state with the new messages
    updated_messages = state["messages"] + [HumanMessage(content=user_input)]
    
    return {
        **state,
        "messages": updated_messages,
        "action": action
    }

def answer_directly(state: SupervisorState) -> Dict[str, Any]:
    """
    Generate a direct response to the user's query without using other agents
    """
    # Extract the user input and the conversation history
    user_input = state["user_input"]
    messages = state["messages"]
    
    # Get the AI model to use
    model = get_model("gpt-4-turbo")
    
    # Set up system prompt
    system_prompt = """
    You are a helpful AI assistant. Answer the user's question directly and concisely.
    If you don't know the answer, say so rather than making something up.
    """
    
    # Build the message list
    ai_messages = [
        SystemMessage(content=system_prompt),
        *messages  # Include the conversation history
    ]
    
    # Get the AI model's response
    response = model.invoke(ai_messages)
    
    # Update the state with the new messages
    updated_messages = messages + [response]
    
    return {
        **state,
        "messages": updated_messages,
        "action": None  # Clear the action since we're done
    }


def create_plan(state: SupervisorState) -> Dict[str, Any]:
    """
    Create a plan for multiple agents to solve the user's request
    """
    # Extract necessary state
    user_input = state["user_input"]
    crew_id = state["crew_id"]
    messages = state["messages"]
    agents = state["agents"]
    
    # Get agent names for the plan
    agent_names = [agent["agent_name"] for _, agent in agents.items()]
    
    # Get the AI model to use
    model = get_model("gpt-4-turbo")
    
    # Set up system prompt
    system_prompt = f"""
    You are a planning AI that creates execution plans for a team of specialized agents.
    
    Available agents: {', '.join(agent_names)}
    
    Based on the user's request, create a step-by-step plan where each step is assigned to a specific agent.
    Return the plan as a JSON object with the following structure:
    ```json
    {{
        "goal": "The overall goal to achieve",
        "steps": [
            {{
                "step": 1,
                "agent": "<agent_name>",
                "task": "<detailed task description>"
            }}
            // More steps...
        ]
    }}
    ```
    
    ONLY return the JSON, no explanation or other text.
    """
    
    # Build the message list
    planning_messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_input)
    ]
    
    # Get the AI model's response
    response = model.invoke(planning_messages)
    
    # Extract and parse the plan JSON
    try:
        # Find JSON between triple backticks if present
        content = response.content
        if "```json" in content and "```" in content.split("```json", 1)[1]:
            json_str = content.split("```json", 1)[1].split("```", 1)[0]
        elif "```" in content and "```" in content.split("```", 1)[1]:
            json_str = content.split("```", 1)[1].split("```", 1)[0]
        else:
            json_str = content
            
        plan = json.loads(json_str)
        
        # Add log message about the plan
        plan_message = f"Plan created with {len(plan['steps'])} steps to achieve: {plan['goal']}"
        
        # Update the state with the new plan and messages
        plan_summary = AIMessage(content=plan_message)
        updated_messages = messages + [plan_summary]
        
        return {
            **state,
            "messages": updated_messages,
            "plan": plan,
            "action": SupervisorAction.ASSIGN_TASKS
        }
    except (json.JSONDecodeError, KeyError) as e:
        # Handle the case where plan creation failed
        error_message = f"Failed to create a valid plan: {str(e)}"
        error_ai_message = AIMessage(content=error_message)
        updated_messages = messages + [error_ai_message]
        
        return {
            **state,
            "messages": updated_messages,
            "action": SupervisorAction.ANSWER_DIRECTLY  # Fall back to direct answering
        }


def assign_tasks(state: SupervisorState) -> Dict[str, Any]:
    """
    Assign tasks to agents based on the plan
    """
    # Extract necessary state
    plan = state["plan"]
    messages = state["messages"]
    agents_state = state["agents"]
    
    # If there's no plan, return the current state
    if not plan or not plan.get("steps"):
        return state
    
    # Initialize any agents that have tasks in the plan
    updated_agents = {**agents_state}
    
    # Create a mapping from agent name to agent id
    agent_name_to_id = {}
    for agent_id, agent in agents_state.items():
        agent_name_to_id[agent["agent_name"]] = agent_id
    
    # Find the first unassigned step in the plan
    next_step = None
    for step in plan["steps"]:
        agent_name = step["agent"]
        if agent_name in agent_name_to_id:
            agent_id = agent_name_to_id[agent_name]
            agent_state = agents_state[agent_id]
            
            # If the agent is idle, assign the task
            if agent_state["status"] == "idle":
                next_step = step
                break
    
    # If no next step found, all tasks are already assigned
    if not next_step:
        # Check if all agents have completed their tasks
        all_complete = all(
            agent["status"] == "complete"
            for agent_id, agent in updated_agents.items()
            if any(step["agent"] == agent["agent_name"] for step in plan["steps"])
        )
        
        if all_complete:
            # All tasks are complete, move to combining results
            return {
                **state,
                "agents": updated_agents,
                "action": SupervisorAction.COMBINE_RESULTS
            }
        else:
            # Some agents are still working, check their status
            return {
                **state,
                "agents": updated_agents,
                "action": SupervisorAction.CHECK_STATUS
            }
    
    # Assign the task to the agent
    agent_name = next_step["agent"]
    task = next_step["task"]
    agent_id = agent_name_to_id[agent_name]
    
    # Update the agent's state
    updated_agents[agent_id] = {
        **updated_agents[agent_id],
        "status": "working",
        "messages": updated_agents[agent_id]["messages"] + [HumanMessage(content=task)]
    }
    
    # Add a message indicating the task assignment
    assignment_message = f"Assigned task to {agent_name}: {task}"
    updated_messages = messages + [AIMessage(content=assignment_message)]
    
    return {
        **state,
        "messages": updated_messages,
        "agents": updated_agents,
        "action": SupervisorAction.CHECK_STATUS  # Next, check status of the agents
    }


def check_status(state: SupervisorState) -> Dict[str, Any]:
    """
    Check the status of all working agents and update their state
    """
    # Extract necessary state
    agents_state = state["agents"]
    messages = state["messages"]
    
    # Find agents that are working
    working_agents = {
        agent_id: agent
        for agent_id, agent in agents_state.items()
        if agent["status"] == "working"
    }
    
    # If no agents are working, return to assign_tasks to find the next task
    if not working_agents:
        return {
            **state,
            "action": SupervisorAction.ASSIGN_TASKS
        }
    
    # In a real implementation, we would check if agents have completed their tasks
    # For this demonstration, we'll simulate agent responses
    updated_agents = {**agents_state}
    status_messages = []
    
    for agent_id, agent in working_agents.items():
        # Get the last task assigned to this agent
        task = None
        for msg in reversed(agent["messages"]):
            if isinstance(msg, HumanMessage):
                task = msg.content
                break
        
        if not task:
            continue
            
        # Get the model for the agent
        model = get_model("gpt-3.5-turbo")
        
        # Simulate the agent processing the task
        agent_name = agent["agent_name"]
        agent_system_prompt = f"You are {agent_name}, an AI agent. Complete the assigned task to the best of your abilities."
        
        # Create a message list for the agent
        agent_messages = [
            SystemMessage(content=agent_system_prompt),
            *agent["messages"][-5:]  # Include last few messages for context
        ]
        
        # Get the agent's response
        try:
            response = model.invoke(agent_messages)
            
            # Update the agent's state
            updated_agents[agent_id] = {
                **updated_agents[agent_id],
                "status": "complete",
                "messages": updated_agents[agent_id]["messages"] + [response],
                "results": {"task": task, "response": response.content}
            }
            
            status_messages.append(f"{agent_name} completed task: {task[:30]}...")
        except Exception as e:
            # Handle errors in agent processing
            updated_agents[agent_id] = {
                **updated_agents[agent_id],
                "status": "error",
                "messages": updated_agents[agent_id]["messages"] + [AIMessage(content=f"Error: {str(e)}")]
            }
            status_messages.append(f"{agent_name} encountered an error: {str(e)}")
    
    # Add status messages to the conversation
    status_update = "\n".join(status_messages)
    updated_messages = messages + [AIMessage(content=status_update)]
    
    # Check if we need to assign more tasks or combine results
    action = SupervisorAction.ASSIGN_TASKS
    
    return {
        **state,
        "messages": updated_messages,
        "agents": updated_agents,
        "action": action
    }


def combine_results(state: SupervisorState) -> Dict[str, Any]:
    """
    Combine results from all agents to create a comprehensive response
    """
    # Extract necessary state
    user_input = state["user_input"]
    messages = state["messages"]
    agents_state = state["agents"]
    plan = state["plan"]
    
    # Collect results from all agents
    results = []
    for agent_id, agent in agents_state.items():
        if agent["results"]:
            results.append(f"Agent {agent['agent_name']}:\n{agent['results']['response']}\n")
    
    # Get the AI model to use
    model = get_model("gpt-4-turbo")
    
    # Set up system prompt
    system_prompt = """
    You are a Supervisor AI that combines results from multiple agents into a coherent response.
    Review the original user request and the outputs from each agent, then create a comprehensive response that answers the user's query.
    Your response should be well-structured, concise, and directly address what the user asked.
    """
    
    # Build the prompt for combining results
    prompt = f"""Original user request: {user_input}

Plan goal: {plan['goal'] if plan and 'goal' in plan else 'No specific goal'}

Agent results:
{''.join(results)}

Based on these results, provide a comprehensive response to the user's original request."""
    
    # Build the message list
    combining_messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=prompt)
    ]
    
    # Get the AI model's response
    try:
        response = model.invoke(combining_messages)
        
        # Update the messages with the final response
        updated_messages = messages + [response]
        
        return {
            **state,
            "messages": updated_messages,
            "action": None  # We're done with the workflow
        }
    except Exception as e:
        # Handle errors in result combination
        error_message = f"Error combining results: {str(e)}"
        error_ai_message = AIMessage(content=error_message)
        updated_messages = messages + [error_ai_message]
        
        return {
            **state,
            "messages": updated_messages,
            "action": None  # End the workflow despite the error
        }


def create_supervisor_graph(crew_id: str, agents: List[Dict], system_prompt: str = None):
    """
    Create a LangGraph for a supervisor-coordinated agent crew
    
    Args:
        crew_id: ID of the crew
        agents: List of agent configurations
        system_prompt: Optional custom system prompt for the supervisor
        
    Returns:
        A compiled StateGraph for the supervisor architecture
    """
    # Set up supervisor system prompt if not provided
    if not system_prompt:
        system_prompt = """
        You are a Supervisor AI that coordinates a team of specialized AI agents to solve tasks.
        
        Your responsibilities:
        1. Analyze the user's input to determine if you can answer directly or need to create a plan
        2. If needed, create a plan with specific tasks for your agents
        3. Assign tasks to appropriate agents
        4. Monitor agent progress and collect results
        5. Combine results and provide a final answer to the user
        
        You will coordinate these specialized AI agents:
        {}
        
        Your goal is to provide the most accurate, helpful, and comprehensive responses to user queries.
        """.format("\n".join([f"- {agent['name']}: {agent.get('description', 'No description')}" for agent in agents]))
    
    # Initialize agent states from the provided agent configurations
    agent_states = {}
    for agent_config in agents:
        agent_id = agent_config.get("id") or str(uuid.uuid4())
        agent_states[agent_id] = {
            "agent_id": agent_id,
            "agent_name": agent_config["name"],
            "messages": [],
            "status": "idle",
            "results": None,
            "tools": agent_config.get("tools", [])
        }
    
    # Define the initial state
    initial_state = {
        "messages": [],
        "user_input": None,
        "plan": None,
        "agents": agent_states,
        "crew_id": crew_id,
        "conversation_id": "",  # This will be set when the graph is invoked
        "action": None
    }
    
    # Create the workflow graph
    workflow = StateGraph(SupervisorState)
    
    # Add nodes to the graph
    workflow.add_node("analyze_input", analyze_input)
    workflow.add_node("answer_directly", answer_directly)
    workflow.add_node("create_plan", create_plan)
    workflow.add_node("assign_tasks", assign_tasks)
    workflow.add_node("check_status", check_status)
    workflow.add_node("combine_results", combine_results)
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "analyze_input",
        {
            SupervisorAction.ANSWER_DIRECTLY: "answer_directly",
            SupervisorAction.CREATE_PLAN: "create_plan"
        },
        router
    )
    
    workflow.add_edge("create_plan", "assign_tasks")
    workflow.add_edge("assign_tasks", "check_status")
    
    workflow.add_conditional_edges(
        "check_status",
        {
            SupervisorAction.CHECK_STATUS: "check_status",
            SupervisorAction.COMBINE_RESULTS: "combine_results"
        },
        router
    )
    
    # Set the entry point
    workflow.set_entry_point("analyze_input")
    
    # Define the end nodes
    workflow.add_edge("answer_directly", END)
    workflow.add_edge("combine_results", END)
    
    # Return the compiled graph with the initial state
    return workflow.compile()
    
    # Map agent names to IDs for easier lookup
    agent_name_to_id = {agent["name"]: agent["id"] for agent in agents}
    
    # Get supervisor commands
    supervisor_commands = get_supervisor_commands()
    
    # Define the supervisor function for the edgeless graph
    def supervisor_function(state: SupervisorState) -> SupervisorState:
        # If this is the first message in the conversation, analyze user input
        if len(state["messages"]) == 0 or (len(state["messages"]) == 1 and isinstance(state["messages"][0], HumanMessage)):
            user_input = state["user_input"] or state["messages"][0].content if state["messages"] else ""
            
            available_agents = "\n".join([f"- {agent['name']}: {agent.get('description', 'No description')}" for agent in agents])
            
            prompt = f"""
            User request: {user_input}
            
            Available agents:
            {available_agents}
            
            Analyze this request and decide if you should:
            1. Answer directly using the 'complete' command if the request is simple, or
            2. Create a plan and assign tasks to agents using the 'assign' command if the request is complex
            
            If you need to create a plan, first describe your plan briefly, then use 'assign' commands to delegate tasks.
            """
            
            messages = [HumanMessage(content=prompt)]
            response = supervisor_model.invoke(messages)
            
            # Add the user input and response to messages
            new_messages = state["messages"].copy()
            if not any(isinstance(msg, HumanMessage) for msg in new_messages):
                new_messages.append(HumanMessage(content=user_input))
            
            # Parse the response for commands
            try:
                commands = parse_command_for_function_calling(response.content, supervisor_commands)
                
                if commands:
                    command = commands[0]
                    if command["name"] == "assign":
                        # Extract agent name and task
                        agent_name = command["arguments"]["agent_name"]
                        task = command["arguments"]["task"]
                        
                        # Create a plan if it doesn't exist
                        plan = state.get("plan", {})
                        if not plan:
                            plan = {"steps": [], "goal": user_input}
                        
                        # Add the step to the plan
                        plan["steps"] = plan.get("steps", []) + [{"agent": agent_name, "task": task}]
                        
                        # Find the agent ID by name
                        agent_id = agent_name_to_id.get(agent_name)
                        if not agent_id:
                            raise CommandException(f"Agent {agent_name} not found")
                        
                        # Update the agent state
                        new_agents = state["agents"].copy()
                        new_agents[agent_id] = {
                            **new_agents[agent_id],
                            "status": "working",
                            "messages": new_agents[agent_id]["messages"] + [HumanMessage(content=task)]
                        }
                        
                        # Convert command to a message
                        command_msg = command_to_message(command)
                        new_messages.append(command_msg)
                        
                        return {
                            **state,
                            "messages": new_messages,
                            "agents": new_agents,
                            "plan": plan,
                            "current_agent": agent_id,
                            "is_complete": False
                        }
                    
                    elif command["name"] == "complete":
                        # Handle completion command
                        summary = command["arguments"]["summary"]
                        
                        # Add the final response to messages
                        new_messages.append(AIMessage(content=summary))
                        
                        # Reset agent states
                        new_agents = state["agents"].copy()
                        for agent_id in new_agents:
                            new_agents[agent_id] = {**new_agents[agent_id], "status": "idle", "results": None}
                        
                        return {
                            **state,
                            "messages": new_messages,
                            "agents": new_agents,
                            "plan": None,
                            "current_agent": None,
                            "is_complete": True
                        }
                else:
                    # No command found, treat as direct answer
                    new_messages.append(response)
                    return {
                        **state,
                        "messages": new_messages,
                        "is_complete": True
                    }
            except Exception as e:
                # If command parsing fails, treat as direct answer
                new_messages.append(response)
                return {
                    **state,
                    "messages": new_messages,
                    "is_complete": True
                }
        
        # If we have an active agent, process its response
        elif state["current_agent"]:
            agent_id = state["current_agent"]
            agent_state = state["agents"][agent_id]
            
            # Simulate agent processing and results
            # In a real implementation, we would invoke the agent model here
            agent_result = f"Results from {agent_state['agent_name']}: Analysis of the task complete."
            
            # Update agent state
            new_agents = state["agents"].copy()
            new_agents[agent_id] = {
                **new_agents[agent_id],
                "status": "complete",
                "results": agent_result,
                "messages": new_agents[agent_id]["messages"] + [AIMessage(content=agent_result)]
            }
            
            # Check if all agents with tasks are complete
            all_tasks_complete = True
            for step in state["plan"]["steps"]:
                agent_name = step["agent"]
                agent_id_for_step = agent_name_to_id.get(agent_name)
                if agent_id_for_step and new_agents[agent_id_for_step]["status"] != "complete":
                    all_tasks_complete = False
                    break
            
            new_messages = state["messages"].copy()
            
            # If all tasks are complete, generate final response
            if all_tasks_complete:
                # Gather all agent results
                results = []
                for a_id, a_state in new_agents.items():
                    if a_state["results"]:
                        results.append(f"- {a_state['agent_name']}: {a_state['results']}")
                
                results_text = "\n".join(results) if results else "No results available."
                
                prompt = f"""
                User request: {state['user_input']}
                
                Agent results:
                {results_text}
                
                Please provide a comprehensive response to the user's request based on these results.
                Use the 'complete' command with a summary of your findings.
                """
                
                messages = [HumanMessage(content=prompt)]
                response = supervisor_model.invoke(messages)
                
                try:
                    # Parse for complete command
                    commands = parse_command_for_function_calling(response.content, supervisor_commands)
                    if commands and commands[0]["name"] == "complete":
                        summary = commands[0]["arguments"]["summary"]
                        new_messages.append(AIMessage(content=summary))
                    else:
                        # If no command, just use the response directly
                        new_messages.append(response)
                except:
                    # Fallback to direct response
                    new_messages.append(response)
                
                return {
                    **state,
                    "messages": new_messages,
                    "agents": new_agents,
                    "current_agent": None,
                    "is_complete": True
                }
            else:
                # Find the next agent to work with
                next_agent = None
                for step in state["plan"]["steps"]:
                    agent_name = step["agent"]
                    agent_id_for_step = agent_name_to_id.get(agent_name)
                    if agent_id_for_step and new_agents[agent_id_for_step]["status"] == "idle":
                        next_agent = agent_id_for_step
                        # Update the agent state
                        new_agents[next_agent] = {
                            **new_agents[next_agent],
                            "status": "working",
                            "messages": new_agents[next_agent]["messages"] + [
                                HumanMessage(content=step["task"])
                            ]
                        }
                        break
                
                # Return updated state with next agent
                return {
                    **state,
                    "messages": new_messages,
                    "agents": new_agents,
                    "current_agent": next_agent,
                    "is_complete": False
                }
        
        # Otherwise, just return the current state
        return state
    
    # Define function to decide the next step
    def should_continue(state: SupervisorState) -> Union[Literal["continue"], Literal["end"]]:
        """Determine if the workflow should continue or end"""
        if state.get("is_complete", False):
            return "end"
        return "continue"
    
    # Build the edgeless graph
    workflow = StateGraph(SupervisorState)
    
    # Add nodes - in edgeless pattern, we have a single node that handles all logic
    workflow.add_node("supervisor", supervisor_function)
    
    # Connect the supervisor node to itself if work isn't complete
    workflow.add_conditional_edges(
        "supervisor",
        {
            "continue": "supervisor", 
            "end": END
        },
        should_continue
    )
    
    # Set the entry point
    workflow.set_entry_point("supervisor")
    
    # Compile the graph
    # Using the default memory implementation without explicit checkpointer
    return workflow.compile()
