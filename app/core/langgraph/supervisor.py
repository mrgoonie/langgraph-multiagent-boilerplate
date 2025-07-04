"""
LangGraph supervisor architecture implementation

This module implements the core supervisor pattern for multi-agent coordination.
"""
from typing import Any, Dict, List, Optional, TypedDict, Annotated, Literal
from pydantic import BaseModel, Field
import uuid
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
import operator
from langgraph.graph import StateGraph, END
# Latest LangGraph version changes how checkpoints work
# We'll compile without an explicit checkpointer

from app.core.config import settings
from app.services.ai_provider import ai_provider


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


class SupervisorAction(BaseModel):
    """Actions that the supervisor can take"""
    action: Literal["answer", "create_plan", "assign_task", "check_status", "combine_results"]
    details: Dict[str, Any] = Field(default_factory=dict)


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
        3. Assign tasks to appropriate agents based on their capabilities
        4. Monitor agent progress and collect results
        5. Combine results and provide a final answer to the user
        
        Be concise and efficient in your coordination. Ensure all agents have completed their tasks before providing a final answer.
        """
    
    # Create the supervisor agent
    supervisor_model = ai_provider.get_model(model_name="google/gemini-2.5-flash")
    
    # Initialize agent states
    agent_states = {}
    for agent in agents:
        agent_states[agent["id"]] = {
            "agent_id": agent["id"],
            "agent_name": agent["name"],
            "messages": [],
            "status": "idle",
            "results": None,
            "tools": agent.get("tools", [])
        }
    
    # Define node functions for the graph
    
    def analyze_input(state: SupervisorState) -> SupervisorAction:
        """Analyze user input and decide whether to answer directly or create a plan"""
        messages = [HumanMessage(content=f"User request: {state['user_input']}\n\nBased on this request, decide whether you can answer directly or need to create a plan using your team of agents. Respond with just one of these actions: 'answer' or 'create_plan'.")]
        response = supervisor_model.invoke(messages)
        
        if "create_plan" in response.content.lower():
            return SupervisorAction(action="create_plan")
        else:
            return SupervisorAction(action="answer")
    
    def answer_directly(state: SupervisorState) -> SupervisorState:
        """Answer the user query directly without agent assistance"""
        messages = state["messages"].copy()
        messages.append(HumanMessage(content=state["user_input"]))
        
        response = supervisor_model.invoke(messages)
        
        new_messages = state["messages"].copy()
        new_messages.append(HumanMessage(content=state["user_input"]))
        new_messages.append(response)
        
        return {"messages": new_messages, **{k: v for k, v in state.items() if k != "messages"}}
    
    def create_plan(state: SupervisorState) -> SupervisorState:
        """Create a plan for the agents based on user input"""
        # Get available agents and their capabilities
        agent_descriptions = []
        for agent_id, agent_state in state["agents"].items():
            tools_desc = ", ".join([tool["name"] for tool in agent_state["tools"]])
            agent_descriptions.append(
                f"Agent ID: {agent_id}\n"
                f"Agent Name: {agent_state['agent_name']}\n"
                f"Available Tools: {tools_desc}\n"
            )
        
        agent_details = "\n".join(agent_descriptions)
        
        messages = [HumanMessage(content=f"""
        User request: {state['user_input']}
        
        Available agents and their tools:
        {agent_details}
        
        Create a detailed plan to address the user's request using these agents. 
        Structure your response as a JSON object with these fields:
        - summary: Brief description of the overall plan
        - tasks: Array of tasks, each with:
          - task_id: Unique identifier for the task
          - description: What needs to be done
          - agent_id: ID of the agent assigned to this task
          - dependencies: Array of task_ids that must be completed before this task
        """)]
        
        response = supervisor_model.invoke(messages)
        
        # Extract the plan from the response
        # In a real implementation, you would parse the JSON response
        # For simplicity, we're just storing the raw response
        plan = {"raw_plan": response.content}
        
        return {**state, "plan": plan}
    
    def assign_tasks(state: SupervisorState) -> SupervisorState:
        """Assign tasks to agents based on the plan"""
        # In a real implementation, you would parse the plan and assign tasks
        # For this boilerplate, we'll just simulate task assignment
        
        new_agents = state["agents"].copy()
        
        # Update each agent's state to "working"
        for agent_id in new_agents:
            new_agents[agent_id] = {**new_agents[agent_id], "status": "working"}
        
        return {**state, "agents": new_agents}
    
    def check_status(state: SupervisorState) -> SupervisorAction:
        """Check if all agents have completed their tasks"""
        all_complete = all(agent["status"] in ["complete", "error"] 
                          for agent in state["agents"].values())
        
        if all_complete:
            return SupervisorAction(action="combine_results")
        else:
            # In a real implementation, we would wait for agent updates
            # For this boilerplate, we'll just simulate completed tasks
            return SupervisorAction(action="check_status")
    
    def combine_results(state: SupervisorState) -> SupervisorState:
        """Combine results from all agents and create a response"""
        # Gather all agent results
        agent_results = []
        for agent_id, agent_state in state["agents"].items():
            if agent_state["results"]:
                agent_results.append(
                    f"Results from {agent_state['agent_name']}:\n"
                    f"{agent_state['results']}"
                )
        
        results_text = "\n\n".join(agent_results) if agent_results else "No agent results available."
        
        messages = [HumanMessage(content=f"""
        User request: {state['user_input']}
        
        Agent results:
        {results_text}
        
        Please provide a comprehensive response to the user's request based on these results.
        """)]
        
        response = supervisor_model.invoke(messages)
        
        new_messages = state["messages"].copy()
        new_messages.append(HumanMessage(content=state["user_input"]))
        new_messages.append(response)
        
        # Reset agent states for next interaction
        new_agents = state["agents"].copy()
        for agent_id in new_agents:
            new_agents[agent_id] = {**new_agents[agent_id], "status": "idle", "results": None}
        
        return {
            **state,
            "messages": new_messages,
            "agents": new_agents,
            "plan": None
        }
    
    # Build the graph
    workflow = StateGraph(SupervisorState)
    
    # Add nodes
    workflow.add_node("analyze_input", analyze_input)
    workflow.add_node("answer_directly", answer_directly)
    workflow.add_node("create_plan", create_plan)
    workflow.add_node("assign_tasks", assign_tasks)
    workflow.add_node("check_status", check_status)
    workflow.add_node("combine_results", combine_results)
    
    # Add edges
    workflow.add_conditional_edges(
        "analyze_input",
        {
            "answer": "answer_directly",
            "create_plan": "create_plan"
        },
        lambda state, action: action.action
    )
    workflow.add_edge("create_plan", "assign_tasks")
    workflow.add_conditional_edges(
        "check_status",
        {
            "check_status": "check_status",  # Loop until complete
            "combine_results": "combine_results"
        },
        lambda state, action: action.action
    )
    
    # Set the entry point and end nodes
    workflow.set_entry_point("analyze_input")
    workflow.add_edge("answer_directly", END)
    workflow.add_edge("combine_results", END)
    workflow.add_edge("assign_tasks", "check_status")
    
    # Compile the graph
    # Using the default memory implementation without explicit checkpointer
    return workflow.compile()
