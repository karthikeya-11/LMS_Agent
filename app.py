import streamlit as st
from datetime import datetime
import os

# Import your HR bot functions from the improved module
from hr_leave_bot import process_message, verify_credentials, get_employee_name
from hr_leave_bot import check_leave_balance, view_leave_history, get_leave_policy, get_holidays, parse_nlp_leave_request

# Configure the page
st.set_page_config(page_title="HR Leave Management Assistant", page_icon="🗓️", layout="wide")

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    
if "employee_id" not in st.session_state:
    st.session_state.employee_id = None
    
if "employee_name" not in st.session_state:
    st.session_state.employee_name = None
    
if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "first_login" not in st.session_state:
    st.session_state.first_login = True

# Custom function to reset the conversation
def reset_conversation():
    st.session_state.messages = []
    
# Custom function to handle logout
def handle_logout():
    st.session_state.authenticated = False
    st.session_state.employee_id = None
    st.session_state.employee_name = None
    st.session_state.messages = []
    st.session_state.first_login = True

# Set OpenAI API key from Streamlit secrets or environment
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    # In production, use Streamlit secrets
    if "openai_api_key" in st.secrets:
        api_key = st.secrets["openai_api_key"]

# Main page content
st.title("🗓️ HR Leave Management Assistant")

# Create sidebar for additional options
with st.sidebar:
    st.subheader("About")
    st.write("This assistant helps you manage your leave requests, check balances, and understand company policies.")
    
    if st.session_state.authenticated:
        st.divider()
        st.subheader("👤 User Profile")
        st.info(f"Logged in as: {st.session_state.employee_name}\nID: {st.session_state.employee_id}")
        
        st.divider()
        st.subheader("⚙️ Options")
        if st.button("Clear Conversation", use_container_width=True):
            reset_conversation()
            st.rerun()
        
        if st.button("Logout", use_container_width=True):
            handle_logout()
            st.rerun()

# Authentication section
if not st.session_state.authenticated:
    st.write("👋 Welcome to the HR Leave Management System!")
    st.write("Please login to continue.")
    
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            employee_id = st.text_input("Employee ID", placeholder="Enter your employee ID")
        with col2:
            password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            login_button = st.button("Login", use_container_width=True)
        
        if login_button:
            if not employee_id or not password:
                st.error("Please enter both Employee ID and Password")
            elif verify_credentials(employee_id, password):
                employee_name = get_employee_name(employee_id)
                st.session_state.authenticated = True
                st.session_state.employee_id = employee_id
                st.session_state.employee_name = employee_name
                st.session_state.first_login = True
                st.rerun()
            else:
                st.error("Invalid credentials. Please try again.")
else:
    # Add welcome message if this is the first login
    if st.session_state.first_login:
        greeting_message = f"Hello {st.session_state.employee_name}! 👋 How can I assist you with leave management today?"
        st.session_state.messages.append({"role": "assistant", "content": greeting_message})
        st.session_state.first_login = False
    
    # Display chat messages
    message_container = st.container()
    with message_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
    
    # Quick action buttons in a more organized layout
    st.divider()
    st.subheader("🚀 Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Check Leave Balance", use_container_width=True):
            response = check_leave_balance(st.session_state.employee_id)
            st.session_state.messages.append({"role": "user", "content": "Check my leave balance"})
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()
    
    with col2:
        if st.button("View Leave History", use_container_width=True):
            response = view_leave_history(st.session_state.employee_id)
            st.session_state.messages.append({"role": "user", "content": "Show my leave history"})
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()
    
    with col3:
        if st.button("View Holidays", use_container_width=True):
            response = get_holidays()
            st.session_state.messages.append({"role": "user", "content": "Show upcoming holidays"})
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()
    
    # Request Leave form
    st.divider()
    st.subheader("📝 Request Leave")
    
    with st.expander("Create New Leave Request"):
        with st.form("leave_request_form"):
            leave_type = st.selectbox("Leave Type", ["annual", "sick", "personal", "bereavement", "maternity", "paternity"])
            
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date")
            with col2:
                end_date = st.date_input("End Date")
                
            reason = st.text_area("Reason for Leave")
            submit_button = st.form_submit_button("Submit Leave Request")
            
        if submit_button:
            # Format dates
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")
            
            # Prepare request text for NLP processing
            request_text = f"I'd like to request {leave_type} leave from {start_date_str} to {end_date_str}" 
            if reason:
                request_text += f" because {reason}"
                
            st.session_state.messages.append({"role": "user", "content": request_text})
            
            with st.spinner("Processing your request..."):
                response = parse_nlp_leave_request(st.session_state.employee_id, request_text)
                st.session_state.messages.append({"role": "assistant", "content": response})
            
            st.rerun()
    
    # Leave Policies section
    with st.expander("View Leave Policies"):
        policies = get_leave_policy()
        st.write(policies)
    
    # Chat input - Process with NLP
    if prompt := st.chat_input("How can I assist with your leave management needs?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.spinner("Thinking..."):
            # Handle common direct queries without going through the full agent
            if any(keyword in prompt.lower() for keyword in ["balance", "how many days", "leave left"]):
                response = check_leave_balance(st.session_state.employee_id)
            elif any(keyword in prompt.lower() for keyword in ["history", "previous leaves", "past leaves"]):
                response = view_leave_history(st.session_state.employee_id)
            elif any(keyword in prompt.lower() for keyword in ["policy", "policies", "rules"]):
                response = get_leave_policy()
            elif any(keyword in prompt.lower() for keyword in ["holiday", "holidays", "day off"]):
                response = get_holidays()
            # For leave requests or more complex queries, use the agent
            elif any(keyword in prompt.lower() for keyword in ["request", "apply", "take", "want", "need"]) and \
                 any(leave_type in prompt.lower() for leave_type in ["annual", "sick", "personal", "bereavement", "maternity", "paternity"]):
                response = parse_nlp_leave_request(st.session_state.employee_id, prompt)
            else:
                # For more complex queries, use the full LangChain agent
                response = process_message(st.session_state.employee_id, prompt)
                
            st.session_state.messages.append({"role": "assistant", "content": response})
        
        st.rerun()