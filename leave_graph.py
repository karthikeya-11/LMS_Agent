# leave_graph.py (Refactored Concepts)
from typing import Dict, Any, List, TypedDict, Annotated, Sequence, Tuple 
import operator
from datetime import datetime

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
# Use ChatOpenAI for tool calling capabilities
from langchain_openai import ChatOpenAI 
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode # Use prebuilt ToolNode
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage # Make sure ToolMessage is imported if needed

# Import tools and data functions
from leave_tools import (
    check_leave_balance,
    view_leave_history,
    get_leave_policy,
    get_holidays,
    check_and_process_leave,
    update_leave_status,
    parse_nlp_leave_request
)
from leave_data import get_employee_name

# --- 1. Update AgentState ---
# Use add_messages for easier message handling
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    employee_id: str
    # Remove current_date if not strictly needed or pass differently
    # Add any other state needed, e.g., tracked missing info

# --- 2. Initialize LLM and Tools ---
# Ensure the model used supports tool calling well (e.g., newer GPT models)
llm = ChatOpenAI(model="gpt-4o", temperature=0) # Or another tool-calling capable model

# Define the tools for the agent
# Option A: Use tools directly
tools = [
    check_leave_balance,
    view_leave_history,
    get_leave_policy,
    get_holidays,
    check_and_process_leave,
    update_leave_status,
    parse_nlp_leave_request
]
# Bind tools to LLM
llm_with_tools = llm.bind_tools(tools)

# Use LangGraph's ToolNode for easier execution
tool_node = ToolNode(tools)

# --- 3. Define System Prompt ---
# Keep the system prompt similar, but ensure it guides the LLM on tool usage
# --- 3. Define System Prompt ---
SYSTEM_PROMPT = """You are an HR Assistant chatbot specializing in leave management.
Your job is to help employees check their leave balances, submit leave requests, and understand company leave policies.

**Carefully review the conversation history provided in the messages to understand the context.** Remember details provided earlier in the conversation (like dates, leave types, or balance information) to avoid asking redundant questions.

Current date: {current_date} 
The user you are speaking with is {employee_name} (Employee ID: {employee_id}).

You have access to the following tools:
- check_leave_balance: Check the employee's current leave balance.
- view_leave_history: View the employee's past leave records.
- get_leave_policy: Get information about specific or all leave policies.
- get_holidays: List upcoming company holidays.
- check_and_process_leave: Use this tool to process a leave request *after* collecting all required information (leave type, start date, end date, reason optional). This tool checks balance, updates the database, and determines auto-approval.
- update_leave_status: Update the status of an existing leave request.
- parse_nlp_leave_request: Use this tool to extract details from a natural language leave request. Ensure you have the necessary details (leave type, start date, end date) from the conversation *before* calling this.

When handling leave requests, follow these steps:
1. Understand the user's intent from their message and the conversation history.
2. If the intent is to request leave, check if you already have the leave type, start date, and end date from the conversation.
3. If any information is missing, ask the user for *all* missing details clearly in one go.
4. Once you have the required information (leave type, start date, end date):
    a. Optionally, check their balance first using `check_leave_balance` if they haven't asked recently or if policy dictates.
    b. Call `check_and_process_leave` to process the request.
5. Inform the user of the outcome (e.g., submitted, pending approval, approved).

Be helpful, professional, and courteous. Use the available tools appropriately based on the user's request and the conversation context. Do not make up information.
"""

# --- 4. Define Graph Nodes ---

# Agent Node: Decides whether to call a tool or respond
def agent_node(state: AgentState):
    print("---AGENT NODE---")
    employee_id = state["employee_id"]
    employee_name = get_employee_name(employee_id)
    current_date = datetime.now().strftime("%Y-%m-%d") # Get current date here

    # Format messages for the prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT.format(current_date=current_date, employee_name=employee_name, employee_id=employee_id)),
        MessagesPlaceholder(variable_name="messages"),
    ])
    
    # Chain the prompt and LLM
    agent_runnable = prompt | llm_with_tools
    
    # Invoke the agent
    response = agent_runnable.invoke({"messages": state["messages"]})
    print(f"Agent response: {response}")
    # The response will be AIMessage, possibly with tool_calls
    return {"messages": [response]}

# Conditional Edge Logic: Decides the next step
def should_continue(state: AgentState) -> str:
    print("---SHOULD CONTINUE?---")
    last_message = state["messages"][-1]
    # If the LLM made tool calls, route to the tool node
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
         print("Decision: Call tool")
         return "call_tool"
    # Otherwise, respond to the user
    print("Decision: End")
    return "end"

# --- 5. Create the Graph ---
def create_leave_management_graph():
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("action", tool_node) # Using the prebuilt ToolNode

    # Set entry point
    workflow.set_entry_point("agent")

    # Add conditional edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "call_tool": "action", # If tool call decided, go to action node
            "end": END,          # If no tool call, end the graph turn
        },
    )

    # Add edge from tool node back to agent node
    # After calling the tool, the result is added to state (by ToolNode)
    # and we loop back to the agent to decide the next step
    workflow.add_edge("action", "agent")

    return workflow.compile()

# Keep the process_message function similar, but adjust state initialization
graph = create_leave_management_graph() # Compile graph once

# def process_message(employee_id: str, current_messages: List[Dict[str, Any]], message: str) -> str:
#     print(f"\nProcessing message for {employee_id}: '{message}'")
#     # Convert current message history dicts to BaseMessage objects if needed
#     # For simplicity, let's assume the Streamlit app passes BaseMessage objects or we convert here
#     # For now, just add the new user message
    
#     # Append new user message
#     messages_for_graph = [HumanMessage(content=message)] # Start with the new message for this turn

#     # If you pass the whole history:
#     # Convert dict messages to BaseMessage objects if needed
#     # history_messages = []
#     # for msg in current_messages:
#     #     if msg["role"] == "user":
#     #         history_messages.append(HumanMessage(content=msg["content"]))
#     #     elif msg["role"] == "assistant":
#     #          # Check if it was a tool call response etc. - more complex state needed
#     #         history_messages.append(AIMessage(content=msg["content"])) 
#     # messages_for_graph = history_messages + [HumanMessage(content=message)]

#     state = {
#         "messages": messages_for_graph, # Pass only the latest message or full converted history
#         "employee_id": employee_id,
#     }
    
#     # Stream the results to see intermediate steps
#     final_state = None
#     print("Invoking graph...")
#     # Use stream or invoke
#     # for output in graph.stream(state):
#     #     # stream() yields dictionaries with output keyed by node name
#     #     for key, value in output.items():
#     #         print(f"Output from node '{key}': {value}")
#     #     print("----")
#     # final_state = list(graph.stream(state))[-1] # Get the final state if needed
    
#     result = graph.invoke(state) # Use invoke for simpler return
#     print(f"Graph result: {result}")

#     # Extract the last AI message (non-tool-calling)
#     response_message = ""
#     if result and result.get("messages"):
#        # Find the last AIMessage that isn't a tool call
#        for msg in reversed(result["messages"]):
#            if isinstance(msg, AIMessage) and not msg.tool_calls:
#                response_message = msg.content
#                break
#            # If the last message is a ToolMessage, the agent might need another turn implicitly handled by invoke/stream loop in a real app
#            # Or sometimes the AIMessage before the ToolMessage has useful text.
#            # This logic might need refinement based on specific agent behavior.
           
#     # Fallback if no suitable message found
#     if not response_message:
#         response_message = "I encountered an issue processing that. Could you please rephrase?"
        
#     print(f"Final response: {response_message}")
#     return response_message


# graph = create_leave_management_graph() # Compile graph once

# Modify process_message to handle history
def process_message(employee_id: str, current_messages: List[Dict[str, Any]], new_user_message: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Processes a new user message, maintaining conversation history.

    Args:
        employee_id: The ID of the employee interacting.
        current_messages: The existing conversation history as a list of dictionaries 
                          (e.g., [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]).
        new_user_message: The latest message input by the user.

    Returns:
        A tuple containing:
        - The AI's response message (str).
        - The updated full conversation history (List[Dict[str, Any]]).
    """
    print(f"\nProcessing message for {employee_id}: '{new_user_message}'")
    
    # 1. Convert dictionary history to BaseMessage objects
    history_messages: List[BaseMessage] = []
    for msg_data in current_messages:
        role = msg_data.get("role")
        content = msg_data.get("content")
        # Basic conversion - might need refinement if you store tool calls/results explicitly in history
        if role == "user":
            history_messages.append(HumanMessage(content=content))
        elif role == "assistant":
             # Important: If the AIMessage had tool calls, you might need to reconstruct
             # that for perfect state, but often just the content is enough for context.
             # For simplicity, we'll just use content here.
             # If the assistant message *was* a tool call result passed back previously,
             # you might need a different role or way to represent it if passing back.
             # However, LangGraph's add_messages handles ToolMessages internally during a run.
            history_messages.append(AIMessage(content=content))
        # Add handling for ToolMessage if you explicitly store tool results in your history dicts

    # 2. Append the new user message
    history_messages.append(HumanMessage(content=new_user_message))

    # 3. Prepare the state for the graph
    state = {
        "messages": history_messages, # Pass the FULL history
        "employee_id": employee_id,
    }

    # 4. Invoke the graph
    print("Invoking graph with history...")
    # Use invoke for a single response, or stream for intermediate steps
    result = graph.invoke(state)
    print(f"Graph result: {result}")

    # 5. Extract the latest AI response message(s) from the result
    # The result["messages"] will contain the history passed in PLUS the new messages added by the graph run
    # (the AI response, possibly ToolMessages and the final AIMessage).
    final_messages_from_graph: List[BaseMessage] = result.get("messages", [])
    
    ai_response_content = ""
    # Find the last AIMessage added by the agent in this run
    if final_messages_from_graph:
         last_message = final_messages_from_graph[-1]
         if isinstance(last_message, AIMessage):
              ai_response_content = last_message.content
         else:
             # Handle cases where the graph might end on a ToolMessage or something else
             # Maybe look backwards for the last AIMessage?
             for msg in reversed(final_messages_from_graph):
                  if isinstance(msg, AIMessage) and not getattr(msg, 'tool_calls', None): # Ensure it's not just initiating a tool call
                       ai_response_content = msg.content
                       break

    # Fallback response
    if not ai_response_content:
        ai_response_content = "Sorry, I encountered an issue. Could you try again?"
        # Add a placeholder AI message to the history if needed
        # final_messages_from_graph.append(AIMessage(content=ai_response_content))


    # 6. Convert the final graph message list back to dictionaries for storage
    updated_history_dicts: List[Dict[str, Any]] = []
    for msg in final_messages_from_graph:
        if isinstance(msg, HumanMessage):
            updated_history_dicts.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
             # Store AI messages (including those that might have made tool calls)
             # You might want to store tool calls/results differently if needed for exact replay
            updated_history_dicts.append({"role": "assistant", "content": msg.content})
        elif isinstance(msg, ToolMessage):
             # Decide how you want to represent tool results in your history storage
             # Option 1: Skip them (context might be inferred from subsequent AI message)
             # Option 2: Store them with a specific role
             # updated_history_dicts.append({"role": "tool", "content": msg.content, "tool_call_id": msg.tool_call_id})
             pass # Skipping for simplicity for now

    print(f"Final response: {ai_response_content}")
    print(f"Updated History Dicts: {updated_history_dicts}")

    return ai_response_content, updated_history_dicts
