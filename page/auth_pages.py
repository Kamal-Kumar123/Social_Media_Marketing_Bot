"""
Authentication pages for the AdBot application.
"""

import streamlit as st
import time
import datetime

def login_page(auth_manager):
    """Display the login page"""
    # Use the built-in auth manager login page
    auth_manager.login_page()

def company_switcher(auth_manager):
    """Display company switcher in the sidebar"""
    user = auth_manager.get_current_user()
    current_company = auth_manager.get_current_company()
    
    if not user:
        return
    
    # Style company section header to match navigation
    st.sidebar.markdown("""
    <div style="background-color: #f0f2f6; padding: 8px; border-radius: 5px; margin-bottom: 10px; margin-top: 20px;">
        <h3 style="margin: 0; color: #262730; font-size: 1.2em;">🏢 Company</h3>
    </div>
    """, unsafe_allow_html=True)
    
    if current_company:
        st.sidebar.markdown(f"""
        <div style="padding: 5px 10px; margin-bottom: 10px; background-color: #f8f9fa; border-radius: 5px; border-left: 3px solid #FF4B4B;">
            <p style="margin: 0; font-weight: bold;">Current: {current_company.get('name', 'Unknown')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Get all companies for the user
    companies = auth_manager.get_user_companies(user["id"])
    
    if len(companies) > 1:
        # Allow user to switch companies
        company_options = {f"{c['name']} ({'Admin' if c['role'] == 'admin' else 'Member'})": c["id"] for c in companies}
        selected_company_name = st.sidebar.selectbox(
            "Select Company", 
            options=list(company_options.keys()),
            key="company_switcher"
        )
        
        col1, col2, col3 = st.sidebar.columns([1, 2, 1])
        with col2:
            if st.button("Switch Company", key="switch_company", use_container_width=True):
                company_id = company_options[selected_company_name]
                if auth_manager.switch_company(company_id):
                    st.success(f"Switched to {selected_company_name}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Failed to switch company")

def team_management_page(auth_manager, data_access):
    """Team management page for company admins"""
    st.title("Team Management")
    
    user = auth_manager.get_current_user()
    company = auth_manager.get_current_company()
    
    if not user or not company:
        st.warning("Please log in to access this page")
        return
    
    # Check if user is admin
    companies = auth_manager.get_user_companies(user["id"])
    is_admin = False
    
    for c in companies:
        if c["id"] == company["id"] and c["role"] == "admin":
            is_admin = True
            break
    
    if not is_admin:
        st.warning("You must be an admin to manage team members")
        return
    
    # Display current team members
    st.markdown("### Team Members")
    
    # Get team members from Firebase
    db = data_access.db
    members_ref = db.collection("company_members").where("company_id", "==", company["id"]).get()
    
    members = []
    for member_doc in members_ref:
        member_data = member_doc.to_dict()
        user_id = member_data.get("user_id")
        
        if user_id:
            user_doc = db.collection("users").document(user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                members.append({
                    "id": user_id,
                    "email": user_data.get("email", "Unknown"),
                    "name": user_data.get("name", "Unknown"),
                    "role": member_data.get("role", "member"),
                    "added_at": member_data.get("added_at", "Unknown")
                })
    
    # Display members table
    if members:
        member_data = []
        for member in members:
            member_data.append({
                "Name": member["name"],
                "Email": member["email"],
                "Role": member["role"].capitalize(),
                "Added": member["added_at"].split("T")[0] if isinstance(member["added_at"], str) else "Unknown"
            })
        
        st.dataframe(member_data)
    else:
        st.info("No team members found")
    
    # Add new member form
    st.markdown("### Add Team Member")
    
    with st.form("add_member_form"):
        email = st.text_input("Email Address")
        role = st.selectbox("Role", options=["member", "admin"])
        
        submitted = st.form_submit_button("Add Member")
        
        if submitted:
            if not email:
                st.error("Email address is required")
            else:
                result = auth_manager.add_company_member(company["id"], email, role)
                
                if result == "success":
                    st.success(f"Added {email} as {role}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Failed to add member: {result}")

def create_company_page(auth_manager):
    """Create a new company page"""
    st.title("Create a New Company")
    
    user = auth_manager.get_current_user()
    
    if not user:
        st.warning("Please log in to create a company")
        return
    
    st.markdown("### New Workspace")
    
    with st.form("create_company_form"):
        company_name = st.text_input("Company Name")
        company_description = st.text_area("Description")
        
        submitted = st.form_submit_button("Create Company")
        
        if submitted:
            if not company_name:
                st.error("Company name is required")
            else:
                try:
                    # Create company in Firebase
                    db = auth_manager.db
                    
                    # Create company
                    company_data = {
                        "name": company_name,
                        "description": company_description,
                        "created_at": datetime.datetime.now().isoformat(),
                        "created_by": user["id"],
                        "plan": "free"  # Default free plan
                    }
                    
                    company_ref = db.collection("companies").add(company_data)
                    company_id = company_ref[1].id
                    
                    # Add user as admin of the company
                    db.collection("company_members").add({
                        "user_id": user["id"],
                        "company_id": company_id,
                        "role": "admin",
                        "added_at": datetime.datetime.now().isoformat()
                    })
                    
                    st.success(f"Created company: {company_name}")
                    
                    # Switch to the new company
                    if auth_manager.switch_company(company_id):
                        time.sleep(1)
                        st.rerun()
                    
                except Exception as e:
                    st.error(f"Error creating company: {str(e)}") 