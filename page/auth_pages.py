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

# Cache user companies to avoid repeated Firebase calls
@st.cache_data(ttl=300)
def get_cached_user_companies(_auth_manager, user_id):
    """Cache user companies data to improve performance"""
    return _auth_manager.get_user_companies(user_id)

def company_switcher(auth_manager):
    """Display company switcher in the sidebar"""
    user = auth_manager.get_current_user()
    current_company = auth_manager.get_current_company()
    
    if not user:
        return
    
    # Use a container to control re-rendering
    company_header = st.sidebar.container()
    
    # Style company section header to match navigation
    company_header.markdown("""
    <div style="background-color: #f0f2f6; padding: 8px; border-radius: 5px; margin-bottom: 10px; margin-top: 20px;">
        <h3 style="margin: 0; color: #262730; font-size: 1.2em;">🏢 Company</h3>
    </div>
    """, unsafe_allow_html=True)
    
    if current_company:
        company_header.markdown(f"""
        <div style="padding: 5px 10px; margin-bottom: 10px; background-color: #f8f9fa; border-radius: 5px; border-left: 3px solid #FF4B4B;">
            <p style="margin: 0; font-weight: bold;">Current: {current_company.get('name', 'Unknown')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Get all companies for the user (using cached function)
    companies = get_cached_user_companies(auth_manager, user["id"])
    
    if len(companies) > 1:
        # Initialize session state for company switching
        if "company_switch_requested" not in st.session_state:
            st.session_state.company_switch_requested = False
            
        # Define callback to avoid full page rerun
        def on_company_change():
            company_id = company_options[st.session_state.selected_company_name]
            st.session_state.company_to_switch = company_id
            
        # Allow user to switch companies
        company_options = {f"{c['name']} ({'Admin' if c['role'] == 'admin' else 'Member'})": c["id"] for c in companies}
        
        # Use session state to preserve selection
        if "selected_company_name" not in st.session_state:
            current_name = next((name for name, id in company_options.items() 
                               if current_company and id == current_company.get("id")), 
                              list(company_options.keys())[0])
            st.session_state.selected_company_name = current_name
            
        st.sidebar.selectbox(
            "Select Company", 
            options=list(company_options.keys()),
            key="selected_company_name",
            on_change=on_company_change
        )
        
        col1, col2, col3 = st.sidebar.columns([1, 2, 1])
        with col2:
            if st.button("Switch Company", key="switch_company", use_container_width=True):
                st.session_state.company_switch_requested = True
                
        # Process company switch request
        if st.session_state.company_switch_requested and hasattr(st.session_state, "company_to_switch"):
            with st.spinner("Switching company..."):
                company_id = st.session_state.company_to_switch
                company_name = st.session_state.selected_company_name
                
                if auth_manager.switch_company(company_id):
                    # Use empty container for status message to control rerun
                    status_placeholder = st.sidebar.empty()
                    status_placeholder.success(f"Switched to {company_name}")
                    
                    # Reset the flag to prevent repeated switching
                    st.session_state.company_switch_requested = False
                    
                    # Delay rerun slightly to show the success message
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.sidebar.error("Failed to switch company")
                    st.session_state.company_switch_requested = False

# Cache team member data to improve performance
@st.cache_data(ttl=60)
def get_cached_team_members(_data_access, company_id):
    """Get cached team members data"""
    db = _data_access.db
    members_ref = db.collection("company_members").where("company_id", "==", company_id).get()
    
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
    return members

def team_management_page(auth_manager, data_access):
    """Team management page for company admins"""
    # Use a lazy-loaded container for the title
    header_container = st.container()
    header_container.title("Team Management")
    
    user = auth_manager.get_current_user()
    company = auth_manager.get_current_company()
    
    if not user or not company:
        st.warning("Please log in to access this page")
        return
    
    # Check if user is admin - use cached user companies
    companies = get_cached_user_companies(auth_manager, user["id"])
    is_admin = any(c["id"] == company["id"] and c["role"] == "admin" for c in companies)
    
    if not is_admin:
        st.warning("You must be an admin to manage team members")
        return
    
    # Use tabs for better organization and performance
    tab1, tab2 = st.tabs(["Team Members", "Add Member"])
    
    with tab1:
        st.markdown("### Team Members")
        
        # Get team members using cached function
        with st.spinner("Loading team members..."):
            members = get_cached_team_members(data_access, company["id"])
        
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
    
    # Add new member form in a separate tab
    with tab2:
        st.markdown("### Add Team Member")
        
        # Initialize session state for the form
        if "add_member_submitted" not in st.session_state:
            st.session_state.add_member_submitted = False
            
        with st.form("add_member_form"):
            email = st.text_input("Email Address")
            role = st.selectbox("Role", options=["member", "admin"])
            
            submitted = st.form_submit_button("Add Member")
            
            if submitted:
                st.session_state.add_member_email = email
                st.session_state.add_member_role = role
                st.session_state.add_member_submitted = True
        
        # Process form submission outside the form to control rerun behavior
        if st.session_state.add_member_submitted:
            email = st.session_state.add_member_email
            role = st.session_state.add_member_role
            
            if not email:
                st.error("Email address is required")
            else:
                with st.spinner("Adding team member..."):
                    result = auth_manager.add_company_member(company["id"], email, role)
                    
                    if result == "success":
                        # Clear the cache to refresh team member data
                        get_cached_team_members.clear()
                        
                        # Use empty container for status message
                        success_placeholder = st.empty()
                        success_placeholder.success(f"Added {email} as {role}")
                        
                        # Reset form state
                        st.session_state.add_member_submitted = False
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(f"Failed to add member: {result}")
                        st.session_state.add_member_submitted = False

def create_company_page(auth_manager):
    """Create a new company page"""
    st.title("Create a New Company")
    
    user = auth_manager.get_current_user()
    
    if not user:
        st.warning("Please log in to create a company")
        return
    
    st.markdown("### New Workspace")
    
    # Initialize session state for company creation
    if "create_company_submitted" not in st.session_state:
        st.session_state.create_company_submitted = False
    
    with st.form("create_company_form"):
        company_name = st.text_input("Company Name")
        company_description = st.text_area("Description")
        
        submitted = st.form_submit_button("Create Company")
        
        if submitted:
            st.session_state.create_company_name = company_name
            st.session_state.create_company_description = company_description
            st.session_state.create_company_submitted = True
    
    # Process company creation outside form to control rerun behavior
    if st.session_state.create_company_submitted:
        company_name = st.session_state.create_company_name
        company_description = st.session_state.create_company_description
        
        if not company_name:
            st.error("Company name is required")
            st.session_state.create_company_submitted = False
        else:
            try:
                with st.spinner("Creating company..."):
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
                    
                    # Clear the user companies cache
                    get_cached_user_companies.clear()
                    
                    success_placeholder = st.empty()
                    success_placeholder.success(f"Created company: {company_name}")
                    
                    # Reset form state
                    st.session_state.create_company_submitted = False
                    
                    # Switch to the new company
                    if auth_manager.switch_company(company_id):
                        time.sleep(0.5)
                        st.rerun()
                
            except Exception as e:
                st.error(f"Error creating company: {str(e)}")
                st.session_state.create_company_submitted = False 