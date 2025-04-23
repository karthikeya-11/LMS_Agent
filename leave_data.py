# leave_data.py
from datetime import datetime, timedelta
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

# Helper functions
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