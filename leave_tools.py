# leave_tools.py
from datetime import datetime
from typing import Optional, List, Dict, Any
from leave_data import EMPLOYEE_DB, LEAVE_TYPES, LEAVE_POLICIES, extract_leave_details

def check_leave_balance(employee_id: str) -> str:
    """Check the current leave balance for the specified employee."""
    if employee_id not in EMPLOYEE_DB:
        return f"Employee ID {employee_id} not found."
    
    balance = EMPLOYEE_DB[employee_id]["leave_balance"]
    name = EMPLOYEE_DB[employee_id]["name"]
    
    response = f"Leave balance for {name} (ID: {employee_id}):\n"
    for leave_type, days in balance.items():
        response += f"- {leave_type.capitalize()} leave: {days} days\n"
    
    return response

def view_leave_history(employee_id: str) -> str:
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

def request_leave(employee_id: str, leave_type: str, start_date: str, end_date: str, reason: str = "") -> str:
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

def get_leave_policy(leave_type: Optional[str] = None) -> str:
    """Get information about leave policies"""
    if leave_type and leave_type.lower() in LEAVE_POLICIES:
        return f"{leave_type.capitalize()} Leave Policy: {LEAVE_POLICIES[leave_type.lower()]}"
    
    response = "Leave Policies:\n"
    for leave_type, policy in LEAVE_POLICIES.items():
        response += f"- {leave_type.capitalize()} Leave: {policy}\n\n"
    
    return response

def get_holidays() -> str:
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

def update_leave_status(employee_id: str, request_id: str, new_status: str) -> str:
    """
    Update the status of a leave request in the database.
    
    Args:
        employee_id: The ID of the employee
        request_id: The ID of the leave request to update
        new_status: The new status to set (e.g., 'approved', 'rejected')
    
    Returns:
        A message indicating the result of the update
    """
    if employee_id not in EMPLOYEE_DB:
        return f"Employee ID {employee_id} not found."
    
    # Find the request in the history
    for record in EMPLOYEE_DB[employee_id]["leave_history"]:
        if record.get("request_id") == request_id:
            old_status = record["status"]
            
            # Update the status
            record["status"] = new_status
            
            # If newly approved, deduct from balance
            if new_status == "approved" and old_status != "approved":
                leave_type = record["type"]
                days = record["days"]
                
                # Only deduct if it's a type that has a balance
                if leave_type in EMPLOYEE_DB[employee_id]["leave_balance"]:
                    # Check if there's enough balance
                    if EMPLOYEE_DB[employee_id]["leave_balance"][leave_type] >= days:
                        EMPLOYEE_DB[employee_id]["leave_balance"][leave_type] -= days
                        return f"Leave request {request_id} status updated from '{old_status}' to '{new_status}'. {days} days deducted from {leave_type} leave balance."
                    else:
                        return f"Warning: Insufficient balance for {leave_type} leave. Status updated but balance not adjusted. Please review."
                
                return f"Leave request {request_id} status updated from '{old_status}' to '{new_status}'."
            
            # If changing from approved to another status, restore the balance
            if old_status == "approved" and new_status != "approved":
                leave_type = record["type"]
                days = record["days"]
                
                # Only add back if it's a type that has a balance
                if leave_type in EMPLOYEE_DB[employee_id]["leave_balance"]:
                    EMPLOYEE_DB[employee_id]["leave_balance"][leave_type] += days
                    return f"Leave request {request_id} status updated from '{old_status}' to '{new_status}'. {days} days restored to {leave_type} leave balance."
            
            return f"Leave request {request_id} status updated from '{old_status}' to '{new_status}'."
    
    return f"No leave request with ID {request_id} found for employee {employee_id}."

def check_and_process_leave(employee_id: str, leave_type: str, start_date: str, end_date: str, reason: str = "") -> str:
    """
    Check leave balance, process the leave request, and update the database accordingly.
    
    Args:
        employee_id: The ID of the employee
        leave_type: The type of leave requested
        start_date: The start date of the leave (YYYY-MM-DD)
        end_date: The end date of the leave (YYYY-MM-DD)
        reason: The reason for the leave request (optional)
    
    Returns:
        A message indicating the result of the leave request processing
    """
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
    name = EMPLOYEE_DB[employee_id]["name"]
    
    # First, check the balance
    balance_info = ""
    has_sufficient_balance = True
    auto_approve = False
    
    if leave_type in EMPLOYEE_DB[employee_id]["leave_balance"]:
        current_balance = EMPLOYEE_DB[employee_id]["leave_balance"][leave_type]
        balance_info = f"Current {leave_type} leave balance: {current_balance} days."
        
        if current_balance >= days:
            has_sufficient_balance = True
            auto_approve = True
            balance_info += f" You have sufficient balance for this {days}-day request."
        else:
            has_sufficient_balance = False
            balance_info += f" You have insufficient balance for this {days}-day request."
    
    # Now process the leave request
    request_id = f"REQ{len(EMPLOYEE_DB[employee_id]['leave_history']) + 1}"
    
    if auto_approve:
        status = "approved"
        # Deduct from balance
        if leave_type in EMPLOYEE_DB[employee_id]["leave_balance"]:
            EMPLOYEE_DB[employee_id]["leave_balance"][leave_type] -= days
        
        approval_msg = f"Leave request automatically approved! Request ID: {request_id}."
    else:
        status = "pending manager approval"
        approval_msg = f"Your leave request has been submitted (Request ID: {request_id}). Status: {status}. You will be notified once your manager reviews it."
    
    # Add to history
    EMPLOYEE_DB[employee_id]["leave_history"].append({
        "request_id": request_id,
        "type": leave_type,
        "start_date": start_date,
        "end_date": end_date,
        "days": days,
        "reason": reason,
        "status": status
    })
    
    # Return a comprehensive message
    return f"{balance_info}\n{approval_msg}"

def parse_nlp_leave_request(employee_id: str, prompt: str) -> str:
    """
    Parses a natural language leave request to extract details and submit it. 
    Use this when a user asks to take time off.
    Args:
        employee_id: The ID of the employee requesting leave.
        prompt: The user's natural language request (e.g., 'I need sick leave tomorrow').
    Returns:
        A message indicating success, failure, or if more information is needed.
    """
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
    
    # Use the new check_and_process_leave function instead of request_leave
    return check_and_process_leave(
        employee_id,
        details["leave_type"],
        details["start_date"],
        details["end_date"],
        details["reason"] or "No reason provided"
    )