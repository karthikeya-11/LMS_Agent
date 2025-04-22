from langchain.agents import Tool, AgentExecutor, create_react_agent
from langchain.memory import ConversationBufferMemory
from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.tools.render import format_tool_to_openai_function
from langchain.schema import SystemMessage, HumanMessage
from datetime import datetime, timedelta
import json
import os
import re

# Sample employee database with passwords
EMPLOYEE_DB = {
    "E001": {
        "name": "Alice Smith",
        "email": "alice@company.com",
        "password": "pass123",  # In production, use hashed passwords
        "leave_balance": {
            "annual": 14,
            "sick": 7,
            "personal": 3
        },
        "leave_history": [
            {
                "type": "annual",
                "start_date": "2025-02-10",
                "end_date": "2025-02-14",
                "status": "approved",
                "days": 5
            }
        ]
    },
    "E002": {
        "name": "Bob Johnson",
        "email": "bob@company.com",
        "password": "pass456",  # In production, use hashed passwords
        "leave_balance": {
            "annual": 20,
            "sick": 10,
            "personal": 3
        },
        "leave_history": []
    }
}

# Leave policies
LEAVE_POLICIES = {
    "annual": "Annual leave requires at least 2 weeks advance notice for periods longer than 3 days. Maximum consecutive days is 15.",
    "sick": "Sick leave can be taken as needed with notification to manager. Doctor's note required for absences longer than 3 consecutive days.",
    "personal": "Personal leave requires 3 days advance notice. Maximum 3 days per year.",
    "bereavement": "Up to 5 days for immediate family members, 2 days for extended family.",
    "maternity": "12 weeks of paid leave available after 1 year of employment.",
    "paternity": "4 weeks of paid leave available after 1 year of employment."
}

# Available leave types
LEAVE_TYPES = ["annual", "sick", "personal", "bereavement", "maternity", "paternity"]

# Tool functions
def check_leave_balance(employee_id):
    """Check the leave balance for an employee"""
    if employee_id not in EMPLOYEE_DB:
        return f"Employee ID {employee_id} not found."
    
    balance = EMPLOYEE_DB[employee_id]["leave_balance"]
    name = EMPLOYEE_DB[employee_id]["name"]
    
    response = f"Leave balance for {name} (ID: {employee_id}):\n"
    for leave_type, days in balance.items():
        response += f"- {leave_type.capitalize()} leave: {days} days\n"
    
    return response

def view_leave_history(employee_id):
    """View leave history for an employee"""
    if employee_id not in EMPLOYEE_DB:
        return f"Employee ID {employee_id} not found."
    
    history = EMPLOYEE_DB[employee_id]["leave_history"]
    name = EMPLOYEE_DB[employee_id]["name"]
    
    if not history:
        return f"{name} has no leave history."
    
    response = f"Leave history for {name} (ID: {employee_id}):\n"
    for record in history:
        response += (f"- {record['type'].capitalize()} leave: {record['start_date']} to {record['end_date']} "
                    f"({record['days']} days) - {record['status']}\n")
    
    return response

def request_leave(employee_id, leave_type, start_date, end_date, reason=""):
    """Submit a leave request"""
    if employee_id not in EMPLOYEE_DB:
        return f"Employee ID {employee_id} not found."
    
    if leave_type.lower() not in LEAVE_TYPES:
        return f"Invalid leave type. Available types: {', '.join(LEAVE_TYPES)}."
    
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        return "Invalid date format. Please use YYYY-MM-DD format."
    
    if start > end:
        return "End date must be after start date."
    
    # Calculate business days
    delta = end - start
    days = delta.days + 1
    
    leave_type = leave_type.lower()
    
    # Check if leave balance is sufficient for annual, sick, personal leave
    if leave_type in EMPLOYEE_DB[employee_id]["leave_balance"]:
        if EMPLOYEE_DB[employee_id]["leave_balance"][leave_type] < days:
            return f"Insufficient {leave_type} leave balance. You requested {days} days but have {EMPLOYEE_DB[employee_id]['leave_balance'][leave_type]} days available. Your request has been forwarded to your manager for special approval."
    
    # Determine if the request can be auto-approved
    can_auto_approve = False
    status = "pending manager approval"
    
    # Auto-approve if it's a standard leave type with sufficient balance
    if leave_type in EMPLOYEE_DB[employee_id]["leave_balance"]:
        if EMPLOYEE_DB[employee_id]["leave_balance"][leave_type] >= days:
            can_auto_approve = True
            status = "approved"
    
    request_id = f"REQ{len(EMPLOYEE_DB[employee_id]['leave_history']) + 1}"
    
    new_request = {
        "request_id": request_id,
        "type": leave_type,
        "start_date": start_date,
        "end_date": end_date,
        "days": days,
        "reason": reason,
        "status": status
    }
    
    # For auto-approved requests, deduct from balance
    if can_auto_approve and leave_type in EMPLOYEE_DB[employee_id]["leave_balance"]:
        EMPLOYEE_DB[employee_id]["leave_balance"][leave_type] -= days
    
    # Add to history
    EMPLOYEE_DB[employee_id]["leave_history"].append({
        "type": leave_type,
        "start_date": start_date,
        "end_date": end_date,
        "days": days,
        "status": status
    })
    
    if can_auto_approve:
        return f"Leave request automatically approved! Request ID: {request_id}. Status: {status}."
    else:
        return f"Your leave request has been submitted (Request ID: {request_id}). Status: {status}. You will be notified once your manager reviews it."

def get_leave_policy(leave_type=None):
    """Get information about leave policies"""
    if leave_type and leave_type.lower() in LEAVE_POLICIES:
        return f"{leave_type.capitalize()} Leave Policy: {LEAVE_POLICIES[leave_type.lower()]}"
    
    response = "Leave Policies:\n"
    for leave_type, policy in LEAVE_POLICIES.items():
        response += f"- {leave_type.capitalize()} Leave: {policy}\n\n"
    
    return response

def get_holidays():
    """Get list of upcoming holidays"""
    # In a real system, this would be connected to a calendar
    holidays = [
        {"date": "2025-05-26", "name": "Memorial Day"},
        {"date": "2025-07-04", "name": "Independence Day"},
        {"date": "2025-09-01", "name": "Labor Day"},
        {"date": "2025-11-27", "name": "Thanksgiving"},
        {"date": "2025-12-25", "name": "Christmas"}
    ]
    
    response = "Upcoming Holidays:\n"
    for holiday in holidays:
        response += f"- {holiday['date']}: {holiday['name']}\n"
    
    return response

def verify_credentials(employee_id, password):
    """Verify employee credentials"""
    if employee_id not in EMPLOYEE_DB:
        return False
    
    return EMPLOYEE_DB[employee_id]["password"] == password

def get_employee_name(employee_id):
    """Get employee name from ID"""
    if employee_id not in EMPLOYEE_DB:
        return None
    
    return EMPLOYEE_DB[employee_id]["name"]

def extract_leave_details(prompt):
    """Extract leave request details from natural language prompt"""
    leave_types_pattern = '|'.join(LEAVE_TYPES)
    
    # Try to find leave type
    leave_type_match = re.search(f"({'|'.join(LEAVE_TYPES)})", prompt.lower())
    leave_type = leave_type_match.group(1) if leave_type_match else None
    
    # Look for dates
    date_pattern = r'(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}|\d{1,2}-\d{1,2}-\d{4})'
    dates = re.findall(date_pattern, prompt)
    
    # Convert to consistent format
    formatted_dates = []
    for date in dates:
        if '/' in date:
            parts = date.split('/')
            if len(parts) == 3:
                try:
                    month, day, year = int(parts[0]), int(parts[1]), int(parts[2])
                    formatted_dates.append(f"{year}-{month:02d}-{day:02d}")
                except ValueError:
                    pass
        elif '-' in date:
            if date.count('-') == 2:
                try:
                    if len(date.split('-')[0]) == 4:  # YYYY-MM-DD
                        formatted_dates.append(date)
                    else:  # MM-DD-YYYY
                        month, day, year = map(int, date.split('-'))
                        formatted_dates.append(f"{year}-{month:02d}-{day:02d}")
                except ValueError:
                    pass
    
    # Get start and end dates if available
    start_date = formatted_dates[0] if formatted_dates else None
    end_date = formatted_dates[1] if len(formatted_dates) > 1 else start_date
    
    # Try to find reason
    reason_patterns = [
        r'(?:reason|for|because):?\s+(.+?)(?:\.|\n|$)',
        r'(?:reason|for|because)\s+(.+?)(?:\.|\n|$)',
        r'(?:due to|as|since)\s+(.+?)(?:\.|\n|$)'
    ]
    
    reason = None
    for pattern in reason_patterns:
        reason_match = re.search(pattern, prompt, re.IGNORECASE)
        if reason_match:
            reason = reason_match.group(1).strip()
            break
    
    return {
        "leave_type": leave_type,
        "start_date": start_date,
        "end_date": end_date,
        "reason": reason
    }

def parse_nlp_leave_request(employee_id, prompt):
    """Parse natural language leave request and process it"""
    details = extract_leave_details(prompt)
    
    missing_info = []
    if not details["leave_type"]:
        missing_info.append("leave type")
    if not details["start_date"]:
        missing_info.append("start date")
    
    if missing_info:
        return f"I need more information to process your leave request. Please provide: {', '.join(missing_info)}."
    
    # If end date wasn't specified, use start date
    if not details["end_date"]:
        details["end_date"] = details["start_date"]
    
    return request_leave(
        employee_id,
        details["leave_type"],
        details["start_date"],
        details["end_date"],
        details["reason"] or "No reason provided"
    )

# Define the tools for the LangChain agent
tools = [
    Tool(
        name="CheckLeaveBalance",
        func=check_leave_balance,
        description="Check an employee's leave balance. Input should be the employee ID (e.g., 'E001')."
    ),
    Tool(
        name="ViewLeaveHistory",
        func=view_leave_history,
        description="View an employee's leave history. Input should be the employee ID (e.g., 'E001')."
    ),
    Tool(
        name="RequestLeave",
        func=request_leave,
        description="Submit a leave request. You should parse the parameters from the conversation and provide them in this order: employee_id, leave_type, start_date (YYYY-MM-DD), end_date (YYYY-MM-DD), and reason."
    ),
    Tool(
        name="GetLeavePolicy",
        func=get_leave_policy,
        description="Get information about leave policies. Input can be a specific leave type (e.g., 'annual', 'sick') or leave blank for all policies."
    ),
    Tool(
        name="GetHolidays",
        func=get_holidays,
        description="Get a list of upcoming company holidays."
    ),
    Tool(
        name="ProcessNLPLeaveRequest",
        func=parse_nlp_leave_request,
        description="Process a natural language leave request. Input should be employee_id and the full leave request text."
    )
]

def create_hr_agent(employee_id=None):
    """Create an HR agent with LangChain"""
    llm = ChatOpenAI(temperature=0)
    
    # Create a proper prompt template for React agent
    template = """You are an HR Assistant chatbot specializing in leave management. 
    Your job is to help employees check their leave balances, submit leave requests, and understand company leave policies.
    
    Current date: {current_date}
    
    Be helpful, professional, and courteous. Focus on understanding the user's intent related to leave management.
    When the user wants to request leave, gather all necessary information: leave type, start date, end date, and reason.
    
    You have access to the following tools:
    {tools}
    """
    
    if employee_id:
        employee_name = get_employee_name(employee_id)
        if employee_name:
            template += f"\nThe current user is {employee_name} (Employee ID: {employee_id})."
    
    # Add the standard React agent template parts
    template += """
    
    Use the following format:
    
    Question: the input question you must answer
    Thought: you should always think about what to do
    Action: the action to take, should be one of [{tool_names}]
    Action Input: the input to the action
    Observation: the result of the action
    ... (this Thought/Action/Action Input/Observation can repeat N times)
    Thought: I now know the final answer
    Final Answer: the final answer to the original input question
    
    Begin!
    
    Question: {input}
    {agent_scratchpad}
    """
    
    prompt = PromptTemplate(
        template=template,
        input_variables=["input", "agent_scratchpad", "current_date", "tools", "tool_names"],
    )
    
    # Create the LangChain agent
    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=prompt
    )
    
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        early_stopping_method="force",
    )

# Function to process user messages with the agent
def process_message(employee_id, user_message):
    """Process a user message with the HR agent"""
    agent = create_hr_agent(employee_id)
    
    # Include the current date in the prompt variables
    response = agent.invoke({
        "input": user_message,
        "current_date": datetime.now().strftime("%Y-%m-%d")
    })
    
    return response["output"]

# Add NLP functionality to better understand leave requests
def enhance_nlp_understanding(text):
    """Enhance NLP understanding of leave requests"""
    # Keywords for leave types
    leave_keywords = {
        "annual": ["annual", "vacation", "holiday", "time off", "days off", "break"],
        "sick": ["sick", "ill", "illness", "doctor", "medical", "health", "unwell"],
        "personal": ["personal", "errands", "appointments", "matters", "affairs"],
        "bereavement": ["bereavement", "funeral", "death", "passed away", "loss"],
        "maternity": ["maternity", "baby", "childbirth", "pregnancy", "pregnant"],
        "paternity": ["paternity", "baby", "childbirth", "new father", "new child"]
    }
    
    # Convert text to lowercase for easier matching
    text_lower = text.lower()
    
    # Detect leave types based on keywords
    detected_types = []
    for leave_type, keywords in leave_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            detected_types.append(leave_type)
    
    # Process time expressions (e.g., "next week", "tomorrow", "for 3 days")
    # This is a simplified implementation - a production system would use a proper NLP library
    time_expressions = {
        "tomorrow": datetime.now() + timedelta(days=1),
        "next week": datetime.now() + timedelta(days=7),
        "next month": datetime.now() + timedelta(days=30),
    }
    
    # Extract time periods
    time_period_pattern = r'(\d+)\s+(day|days|week|weeks|month|months)'
    time_matches = re.findall(time_period_pattern, text_lower)
    
    detected_info = {
        "detected_leave_types": detected_types,
        "time_expressions": {},
        "time_periods": time_matches
    }
    
    for expr, date in time_expressions.items():
        if expr in text_lower:
            detected_info["time_expressions"][expr] = date.strftime("%Y-%m-%d")
    
    return detected_info

# Simple testing function
if __name__ == "__main__":
    # Test the agent
    print(process_message("E001", "What's my leave balance?"))