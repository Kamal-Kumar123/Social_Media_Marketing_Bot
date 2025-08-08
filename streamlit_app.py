"""
AdBot - AI-Powered Social Media Marketing Bot

This streamlit app provides a user-friendly interface for managing 
automated social media marketing campaigns across multiple platforms.
With multi-tenant support, authentication, and pay-as-you-go pricing.
"""

import os
import json
import time
import logging
import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
from PIL import Image
import io
import firebase_admin
from firebase_admin import credentials
from typing import Dict, List, Any
import threading
import asyncio
import concurrent.futures

# Configure logging
logger = logging.getLogger("StreamlitApp")

# Import our models and utilities
from models import Config, ContentGenerator, SocialMediaHandler, AnalyticsManager
from utils import ProductManager, AdScheduler, AuthManager, PaymentManager, DataAccessManager
from page import (
    auth_pages, login_page, company_switcher, team_management_page, create_company_page,
    billing_page, products_page, create_ad_page, schedule_page, analytics_page
)

# Executor for concurrent operations
executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

# Performance improvement: Load components progressively
# This helps with perceived performance by showing UI faster
def load_progressively():
    """Mark that progressive loading is enabled"""
    if "progressive_loading" not in st.session_state:
        st.session_state.progressive_loading = True
        st.session_state.loading_step = 0

# Application state
@st.cache_resource(ttl=3600)  # Cache for 1 hour
def initialize_app():
    """Initialize application components and return them"""
    # Log initialization start
    logger.info("Initializing application components")
    
    # Create directories if they don't exist
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/images", exist_ok=True)
    os.makedirs("data/analytics", exist_ok=True)
    
    # Enable progressive loading
    load_progressively()
    
    try:
        # Explicitly initialize Firebase before anything else
        firebase_cred_path = os.getenv("FIREBASE_CRED_PATH", "firebase-credentials.json")
        if not firebase_admin._apps:
            cred = credentials.Certificate(firebase_cred_path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase initialized successfully in initialize_app()")
    except Exception as e:
        logger.error(f"Error initializing Firebase in initialize_app(): {str(e)}")
        st.error(f"Failed to initialize Firebase: {str(e)}")
        
    # Initialize components with lazy loading where possible
    app_components = {}
    
    # Initialize essential components first
    logger.info("Initializing essential components")
    app_components["config"] = Config()
    app_components["auth_manager"] = AuthManager()
    app_components["data_access"] = DataAccessManager()
    
    # Lazy-load non-essential components
    def load_remaining_components():
        logger.info("Lazy-loading remaining components")
        app_components["content_generator"] = ContentGenerator(app_components["config"])
        app_components["social_handler"] = SocialMediaHandler(app_components["config"])
        app_components["analytics_manager"] = AnalyticsManager(
            app_components["config"], 
            app_components["social_handler"]
        )
        app_components["product_manager"] = ProductManager(app_components["config"])
        app_components["payment_manager"] = PaymentManager()
        
        # Start scheduler last
        app_components["scheduler"] = AdScheduler(
            app_components["config"], 
            app_components["product_manager"], 
            app_components["content_generator"], 
            app_components["social_handler"], 
            app_components["analytics_manager"]
        )
        app_components["scheduler"].start()
        
        logger.info("All components initialized")
        st.session_state.all_components_loaded = True
    
    # Start a background thread to load remaining components
    if "all_components_loaded" not in st.session_state:
        st.session_state.all_components_loaded = False
        threading.Thread(target=load_remaining_components).start()
    
    logger.info("Essential initialization complete")
    return app_components

# Cache for platform status to avoid repeated API calls
@st.cache_data(ttl=60)  # Cache for 1 minute
def get_cached_platform_status(_social_handler):
    """Get cached platform connection status"""
    return _social_handler.get_platform_status()

# Cache for company analytics data
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_cached_company_analytics(_data_access, company_id, days=30):
    """Get cached company analytics data"""
    return _data_access.get_company_analytics(company_id, days)

# Cache for company balance
@st.cache_data(ttl=60)  # Cache for 1 minute
def get_cached_company_balance(_payment_manager, company_id):
    """Get cached company balance"""
    return _payment_manager._get_company_balance(company_id)

# Cache for scheduled posts
@st.cache_data(ttl=60)  # Cache for 1 minute
def get_cached_company_schedules(_data_access, company_id):
    """Get cached company schedules"""
    return _data_access.get_company_schedules(company_id)

# Preload data in background to improve responsiveness
def preload_data(app, company_id):
    """Preload commonly used data in background threads"""
    if not company_id:
        return
        
    def _preload_company_data():
        # Preload data that will likely be needed soon
        try:
            get_cached_platform_status(app["social_handler"])
            get_cached_company_analytics(app["data_access"], company_id, 30)
            get_cached_company_balance(app["payment_manager"], company_id)
            get_cached_company_schedules(app["data_access"], company_id)
            logger.info(f"Preloaded data for company {company_id}")
        except Exception as e:
            logger.error(f"Error preloading data: {str(e)}")
    
    # Run preloading in background thread
    if "preload_running" not in st.session_state:
        st.session_state.preload_running = True
        threading.Thread(target=_preload_company_data).start()

def main():
    """Main application function"""
    # Configure Streamlit page
    st.set_page_config(
        page_title="AdBot - AI Marketing Assistant",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Set up CSS for improved responsiveness
    st.markdown("""
    <style>
    /* Improve loading appearance */
    .stSpinner > div {
        border-color: #FF4B4B !important;
    }
    
    /* Faster transitions */
    div.stButton > button {
        transition: all 0.1s ease;
    }
    
    /* Optimize animations */
    @media (prefers-reduced-motion: reduce) {
        * {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
            scroll-behavior: auto !important;
        }
    }
    
    /* Reduce layout shifts */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    
    /* Custom hamburger menu icon instead of < button */
    button[kind="header"] {
        display: none !important;
    }
    
    /* Add custom hamburger menu */
    .sidebar-toggle {
        position: fixed;
        top: 0.5rem;
        left: 0.5rem;
        z-index: 1000;
        cursor: pointer;
        background: rgba(0, 0, 0, 0.1);
        border-radius: 5px;
        padding: 4px 8px;
        transition: all 0.2s ease;
    }
    
    .sidebar-toggle:hover {
        background: rgba(255, 75, 75, 0.2);
    }
    
    .hamburger-line {
        width: 24px;
        height: 3px;
        background-color: #FF4B4B;
        margin: 5px 0;
        border-radius: 2px;
        transition: 0.4s;
    }
    
    /* Google Sign-in Button Styling */
    .google-btn {
        width: 100%;
        height: 42px;
        background-color: #4285f4;
        border-radius: 2px;
        box-shadow: 0 3px 4px 0 rgba(0,0,0,.25);
        cursor: pointer;
        margin-bottom: 10px;
        display: flex;
    }
    .google-btn .google-icon-wrapper {
        width: 40px;
        height: 42px;
        background-color: #fff;
        border-radius: 2px 0 0 2px;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    .google-btn .google-icon {
        width: 18px;
        height: 18px;
    }
    .google-btn .btn-text {
        color: #fff;
        font-size: 14px;
        font-weight: 500;
        font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Oxygen-Sans,Ubuntu,Cantarell,"Helvetica Neue",sans-serif;
        padding: 11px 20px;
        flex-grow: 1;
        text-align: center;
    }
    .google-btn:hover {
        box-shadow: 0 0 6px #4285f4;
    }
    </style>
    
    <div class="sidebar-toggle" onclick="document.querySelector('button[kind=header]').click()">
        <div class="hamburger-line"></div>
        <div class="hamburger-line"></div>
        <div class="hamburger-line"></div>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        # Use a container for the banner to control rendering
        banner_container = st.container()
        
        # Add fancy banner at the top
        banner_container.markdown("""
        <div style="background: linear-gradient(90deg, #1E1E1E, #3D0000, #1E1E1E); padding: 15px; border-radius: 8px; text-align: center; margin-bottom: 25px; box-shadow: 0 4px 8px rgba(0,0,0,0.3);">
            <h1 style="color: #FF4B4B; font-size: 36px; font-weight: bold; margin: 0; text-shadow: 2px 2px 4px #000000, 0 0 10px #FF0000; letter-spacing: 2px; font-family: 'Arial Black', Gadget, sans-serif;">
                ⚡ LASTAPPSTANDING ⚡
            </h1>
            <p style="color: #E0E0E0; margin-top: 5px; font-style: italic; text-shadow: 1px 1px 2px #000000;">
                Your Ultimate AI Marketing Automation
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Initialize the app
        app = initialize_app()
        
        # Initialize user interface
        if "current_page" not in st.session_state:
            st.session_state["current_page"] = "Home"
        
        # Use layout containers to minimize layout shifts
        auth_container = st.empty()
        sidebar_container = st.empty()
        content_container = st.empty()
        
        # Handle Google OAuth callback
        query_params = st.query_params
        if "code" in query_params:
            with st.spinner("Authenticating with Google..."):
                try:
                    auth_result = app["auth_manager"]._process_oauth_callback(query_params["code"])
                    if auth_result:
                        st.success("Successfully authenticated with Google!")
                        time.sleep(0.5)
                        # Clear query parameters
                        st.query_params.clear()
                        st.rerun()
                    else:
                        st.error("Authentication failed. Please try again.")
                        # Clear query parameters
                        st.query_params.clear()
                except Exception as e:
                    st.error(f"Authentication error: {str(e)}")
                    # Clear query parameters
                    st.query_params.clear()
            
        # Check authentication
        if not app["auth_manager"].is_authenticated():
            with auth_container.container():
                # Custom login page with Google authentication
                st.title("AdBot - Login")
                
                st.markdown(
                    """
                    ### Welcome to AdBot Marketing

                    Sign in to manage your social media marketing campaigns across multiple platforms.
                    """
                )
                
                # Login options
                st.markdown("---")
                st.markdown("### Sign in with:")
                
                col1, col2 = st.columns(2)
                
                # Google login button
                with col1:
                    # Check if Google OAuth is configured
                    client_id = os.getenv("GOOGLE_CLIENT_ID")
                    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
                    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501/callback")

                    if not client_id or client_id == "":
                        st.error("Google OAuth credentials not configured.")
                        st.info("Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables")
                    else:
                        if st.button("Google", key="google_login", use_container_width=True):
                            # Use the _initiate_google_auth method from AuthManager
                            app["auth_manager"]._initiate_google_auth()
                
                # Development/Bypass login button
                with col2:
                    if st.button("📧 Email", key="email_login", use_container_width=True):
                        st.session_state["show_email_form"] = True
                
                # Email login form
                if st.session_state.get("show_email_form", False):
                    with st.form("email_login_form"):
                        st.subheader("Email Login")
                        email = st.text_input("Email")
                        password = st.text_input("Password", type="password")
                        
                        submitted = st.form_submit_button("Login")
                        if submitted:
                            if email and password:
                                # In a real app, validate credentials against Firebase Auth
                                # For now, we'll allow a test account to bypass for development
                                if email == "test@example.com" and password == "password":
                                    # Create a simple test user
                                    test_user = {
                                        "id": "test-user-id",
                                        "email": email,
                                        "name": "Test User",
                                        "picture": f"https://ui-avatars.com/api/?name=Test+User&background=random"
                                    }
                                    
                                    # Store user in session
                                    st.session_state["user"] = test_user
                                    
                                    # Create a test company for the user
                                    test_company = {
                                        "id": "test-company-id",
                                        "name": "Test Company",
                                        "owner": "test-user-id",
                                        "role": "owner",
                                        "plan": "free",
                                        "balance": 100.0,
                                        "members": [
                                            {"id": "test-user-id", "email": email, "role": "owner"}
                                        ]
                                    }
                                    
                                    # Store company in session
                                    st.session_state["company"] = test_company
                                    
                                    # Redirect to main app
                                    st.success("Logged in successfully!")
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error("Invalid email or password")
                            else:
                                st.error("Please enter both email and password")
                
                # Development note
                st.markdown("---")
                st.info("""
                **Google Authentication Setup**:
                1. Make sure your Google Cloud Console OAuth Credentials are configured correctly
                2. Authorized redirect URI must be exactly: http://localhost:8501/callback
                3. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables
                
                **Development Mode:** Email login with test@example.com / password will create a test account
                """)
            return
            
        # Get user and company information
        user = app["auth_manager"].get_current_user()
        company = app["auth_manager"].get_current_company()
        
        # Preload data in background to improve responsiveness when switching pages
        if company:
            preload_data(app, company["id"])
            
        # Setup sidebar
        with sidebar_container.container():
            auth_pages.company_switcher(app["auth_manager"])
        display_sidebar(app)
        
        # Display the current page
        page = st.session_state.get("current_page", "Home")
        with content_container.container():
            display_page(app, page)
            
    except Exception as e:
        # Handle initialization errors
        st.error(f"An error occurred: {str(e)}")
        st.write("If this is related to Firebase, make sure your credentials file is properly set up.")
        
        # Create a simple login button
        if st.button("Try Again"):
            # Clear session state to force reinitialization
            for key in list(st.session_state.keys()):
                if key.startswith("_"):
                    del st.session_state[key]
            st.rerun()

# Maintain dashboard state to prevent recomputing unnecessarily
@st.cache_data(ttl=60)
def get_dashboard_data(_data_access, _social_handler, _payment_manager, company_id, user_id, days=30):
    """Get all dashboard data in one efficient call"""
    # Run multiple data fetches concurrently
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Start all data fetching tasks
        platform_status_future = executor.submit(get_cached_platform_status, _social_handler)
        analytics_future = executor.submit(get_cached_company_analytics, _data_access, company_id, days)
        balance_future = executor.submit(get_cached_company_balance, _payment_manager, company_id)
        schedules_future = executor.submit(get_cached_company_schedules, _data_access, company_id)
        
        # Get results from all futures
        platform_status = platform_status_future.result()
        analytics = analytics_future.result()
        balance = balance_future.result()
        schedules = schedules_future.result()
    
    return {
        "platform_status": platform_status,
        "analytics": analytics,
        "balance": balance,
        "schedules": schedules
    }

def dashboard_page(app):
    """Dashboard page showing key metrics and status"""
    # Use a simple title like in analytics_page
    st.title("Dashboard")
    
    # Get current user and company
    user = app["auth_manager"].get_current_user()
    company = app["auth_manager"].get_current_company()
    
    if not user or not company:
        st.warning("Please select a company to continue.")
        return
    
    # Welcome message
    st.subheader(f"Welcome, {user.get('name', 'User')}!")
    st.write(f"**Current Workspace:** {company.get('name', 'Unknown')}")
    
    # Loading indicator
    with st.spinner("Loading dashboard data..."):
        try:
            # Get all dashboard data in a single efficient call
            dashboard_data = get_dashboard_data(
                app["data_access"], 
                app["social_handler"],
                app["payment_manager"],
                company["id"],
                user["id"]
            )
            
            # Get data from dashboard_data
            platform_status = dashboard_data["platform_status"]
            analytics = dashboard_data["analytics"]
            balance = dashboard_data["balance"]
            schedules = dashboard_data["schedules"]
            
            # Get company plan
            plan = company.get("plan", "free")
            plan_details = app["payment_manager"].plans.get(plan, {})
            
            # Show plan information
            st.write(f"**Current Plan:** {plan_details.get('name', plan.capitalize())}")
            
            # Add a separator
            st.markdown("---")
            
            # Performance Metrics section
            st.subheader("Performance Metrics")
            
            # Create metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                active_platforms = sum(1 for status in platform_status.values() if status == "connected")
                available_platforms = plan_details.get("platforms", 0)
                
                if isinstance(available_platforms, str) and available_platforms.lower() == "all":
                    platform_text = f"{active_platforms} / All"
                else:
                    platform_text = f"{active_platforms} / {available_platforms}"
                    
                st.metric(
                    label="Active Platforms", 
                    value=platform_text
                )
            
            with col2:
                total_posts = analytics.get("total_posts", 0)
                monthly_limit = plan_details.get("monthly_posts", 0)
                
                if isinstance(monthly_limit, str) and monthly_limit.lower() == "unlimited":
                    posts_text = f"{total_posts} / Unlimited"
                else:
                    posts_text = f"{total_posts} / {monthly_limit}"
                    
                st.metric(
                    label="Posts (30 days)", 
                    value=posts_text
                )
            
            with col3:
                credit_balance = balance.get("balance", 0)
                
                st.metric(
                    label="Credit Balance", 
                    value=f"${credit_balance:.2f}"
                )
            
            with col4:
                scheduled_posts = len([s for s_id, s in schedules.items() if s.get("status") == "scheduled"])
                
                st.metric(
                    label="Scheduled Posts", 
                    value=scheduled_posts
                )
            
            # Add a separator
            st.markdown("---")
            
            # Quick Actions section
            st.subheader("Quick Actions")
            
            quick_col1, quick_col2, quick_col3, quick_col4 = st.columns(4)
            
            with quick_col1:
                if st.button("📝 Create New Ad", key="dashboard_create_ad", use_container_width=True):
                    st.session_state["current_page"] = "Create Ad"
                    st.rerun()
            
            with quick_col2:
                if st.button("🗓️ Schedule Posts", key="dashboard_schedule", use_container_width=True):
                    st.session_state["current_page"] = "Schedule Posts"
                    st.rerun()
            
            with quick_col3:
                if st.button("📈 View Analytics", key="dashboard_analytics", use_container_width=True):
                    st.session_state["current_page"] = "Analytics"
                    st.rerun()
            
            with quick_col4:
                if st.button("💳 Add Credits", key="dashboard_add_credits", use_container_width=True):
                    st.session_state["current_page"] = "Billing"
                    st.rerun()
            
            # Add a separator
            st.markdown("---")
            
            # Platform engagement if there's data
            if analytics.get("total_posts", 0) > 0:
                st.subheader("Platform Performance")
                
                platform_data = []
                for platform, data in analytics.get("platforms", {}).items():
                    engagement = data.get("engagement", {})
                    total_engagement = sum(engagement.values())
                    
                    platform_data.append({
                        "Platform": platform,
                        "Posts": data.get("post_count", 0),
                        "Total Engagement": total_engagement,
                        "Avg Engagement": total_engagement / data.get("post_count", 1)
                    })
                
                if platform_data:
                    df = pd.DataFrame(platform_data)
                    
                    # Use a lightweight Altair chart instead of heavy bar_chart
                    import altair as alt
                    
                    # Create a visually appealing chart
                    chart = alt.Chart(df).mark_bar().encode(
                        x=alt.X('Platform:N', title=None, sort=None),
                        y=alt.Y('Avg Engagement:Q', title='Average Engagement'),
                        color=alt.Color('Platform:N', 
                                         scale=alt.Scale(scheme='set2'),
                                         legend=None),
                        tooltip=['Platform', 'Posts', 'Total Engagement', 'Avg Engagement']
                    ).properties(
                        height=300
                    )
                    
                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.info("No platform performance data available yet.")
                
                # Add a separator
                st.markdown("---")
            
            # Recent activity section
            st.subheader("Recent Activity")
            
            # Get recent posts with error handling
            try:
                # Get recent posts - use a cached version to improve performance
                @st.cache_data(ttl=120)
                def get_recent_posts(_data_access, company_id, limit=5):
                    try:
                        recent_posts_ref = _data_access.db.collection("posts").where(
                            "company_id", "==", company_id
                        ).order_by("timestamp", direction="DESCENDING").limit(limit).get()
                        return list(recent_posts_ref)
                    except Exception as e:
                        logger.error(f"Error getting recent posts: {str(e)}")
                        return []
                
                recent_posts_ref = get_recent_posts(app["data_access"], company["id"])
                
                if recent_posts_ref:
                    for post in recent_posts_ref:
                        post_data = post.to_dict()
                        platform = post_data.get("platform", "Unknown")
                        product_id = post_data.get("product_id", "Unknown")
                        
                        # Get product name
                        @st.cache_data(ttl=300)
                        def get_product_name(_data_access, product_id, company_id):
                            try:
                                product = _data_access.get_product(product_id, company_id)
                                return product.get("name", product_id) if product else product_id
                            except Exception:
                                return product_id
                        
                        product_name = get_product_name(app["data_access"], product_id, company["id"])
                        post_time = post_data.get("timestamp", "").split("T")[0] if isinstance(post_data.get("timestamp"), str) else "Unknown"
                        
                        # Use the same post card styling as in analytics page
                        st.markdown(f"""
                        <div style="border: 1px solid #eee; padding: 15px; margin-bottom: 10px; border-radius: 5px;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                                <span style="font-weight: bold;">{platform.title()}</span>
                                <span style="font-size: 12px; color: #777;">{post_time}</span>
                            </div>
                            <p style="margin-bottom: 10px;">{product_name}</p>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No recent activity. Create some posts to get started!")
            except Exception as e:
                logger.error(f"Error displaying recent activity: {str(e)}")
                st.info("No recent activity data available.")
            
        except Exception as e:
            logger.error(f"Error in dashboard: {str(e)}")
            st.error(f"Error loading dashboard data: {str(e)}")
            
            # Display error message similar to analytics page
            st.markdown("""
            <div style="background-color: #f8d7da; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3 style="margin-top:0; color:#721c24">We encountered an error</h3>
                <p>The dashboard service is currently experiencing some issues. Please try again later.</p>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("Technical Details (for support)"):
                st.code(str(e), language="python")

def platform_setup_page(app):
    """Platform setup and configuration page"""
    st.title("Platform Setup")
    
    # Get current user and company
    user = app["auth_manager"].get_current_user()
    company = app["auth_manager"].get_current_company()
    
    if not user or not company:
        st.warning("Please select a company to continue.")
        return
    
    tab1, tab2 = st.tabs(["Platform Status", "API Configuration"])
    
    with tab1:
        st.markdown("### Platform Connection Status")
        
        # Get platform connection status - use cached version
        platform_status = get_cached_platform_status(app["social_handler"])
        
        # Get company plan
        plan = company.get("plan", "free")
        plan_details = app["payment_manager"].plans.get(plan, {})
        
        # Create status data
        status_data = []
        for platform, status in platform_status.items():
            # ✅ Mark all platforms as available EXCEPT Snapchat
            is_available = platform.lower() != "snapchat"

            icon = "✅" if status == "connected" else "❌"
            
            status_data.append({
                "Platform": platform.title(),
                "Status": f"{icon} {status}",
                "Available in Plan": "✅" if is_available else "❌"
            })
        
        status_df = pd.DataFrame(status_data)
        st.table(status_data)
        
        # Initialize platforms - with improved responsiveness
        if st.button("Refresh Platform Connections", key="refresh_platforms"):
            with st.spinner("Refreshing connections..."):
                app["social_handler"].init_platform_clients()
                # Clear platform status cache
                get_cached_platform_status.clear()
                st.success("Platform connections refreshed!")
                time.sleep(0.3)  # Reduced delay
            st.rerun()

    
    with tab2:
        st.markdown("### API Configuration")
        
        # Create a form placeholder
        form_placeholder = st.empty()
        
        with form_placeholder.form("api_config_form"):
            # st.markdown("#### OpenAI API")
            # openai_api_key = st.text_input("OpenAI API Key", type="password", value=app["config"].openai_api_key)
            
            # Social media platform configs
            platforms = [
                "facebook", "twitter", "instagram", "linkedin", 
                "tiktok", "pinterest", "snapchat"
            ]
            
            for platform in platforms:
                st.markdown(f"#### {platform.title()} API")
                
                if platform == "facebook":
                    facebook_access_token = st.text_input("Access Token", type="password", value=app["config"].facebook_access_token)
                    facebook_app_id = st.text_input("App ID", value=app["config"].facebook_app_id)
                    facebook_app_secret = st.text_input("App Secret", type="password", value=app["config"].facebook_app_secret)
                    facebook_page_id = st.text_input("Page ID", value=app["config"].facebook_page_id)
                
                elif platform == "twitter":
                    twitter_api_key = st.text_input("API Key", type="password", value=app["config"].twitter_api_key)
                    twitter_api_secret = st.text_input("API Secret", type="password", value=app["config"].twitter_api_secret)
                    twitter_access_token = st.text_input("Access Token", type="password", value=app["config"].twitter_access_token)
                    twitter_access_token_secret = st.text_input("Access Token Secret", type="password", value=app["config"].twitter_access_token_secret)
                
                elif platform == "instagram":
                    instagram_username = st.text_input("Username", value=app["config"].instagram_username)
                    instagram_password = st.text_input("Password", type="password", value=app["config"].instagram_password)
                
                elif platform == "linkedin":
                    linkedin_client_id = st.text_input("Client ID", value=app["config"].linkedin_client_id)
                    linkedin_client_secret = st.text_input("Client Secret", type="password", value=app["config"].linkedin_client_secret)
                    linkedin_access_token = st.text_input("Access Token", type="password", value=app["config"].linkedin_access_token)
                
                elif platform == "tiktok":
                    tiktok_access_token = st.text_input("Access Token", type="password", value=app["config"].tiktok_access_token)
                
                elif platform == "pinterest":
                    pinterest_access_token = st.text_input("Access Token", type="password", value=app["config"].pinterest_access_token)
                    pinterest_board_id = st.text_input("Board ID", value=app["config"].pinterest_board_id)
                
                elif platform == "snapchat":
                    snapchat_access_token = st.text_input("Access Token", type="password", value=app["config"].snapchat_access_token)
            
            # Bot configuration
            st.markdown("#### Bot Configuration")
            enabled_platforms = st.multiselect(
                "Enabled Platforms",
                options=platforms,
                default=app["config"].platforms
            )
            
            post_frequency = st.slider(
                "Posts Per Day", 
                1, 24, 
                int(app["config"].post_frequency)
            )
            
            # Submit
            submitted = st.form_submit_button("Save Configuration")
            
            if submitted:
                try:
                    # Create config dict
                    config_dict = {
                        "openai_api_key": openai_api_key,
                        "facebook_access_token": facebook_access_token,
                        "facebook_app_id": facebook_app_id,
                        "facebook_app_secret": facebook_app_secret,
                        "facebook_page_id": facebook_page_id,
                        "twitter_api_key": twitter_api_key,
                        "twitter_api_secret": twitter_api_secret,
                        "twitter_access_token": twitter_access_token,
                        "twitter_access_token_secret": twitter_access_token_secret,
                        "instagram_username": instagram_username,
                        "instagram_password": instagram_password,
                        "linkedin_client_id": linkedin_client_id,
                        "linkedin_client_secret": linkedin_client_secret,
                        "linkedin_access_token": linkedin_access_token,
                        "tiktok_access_token": tiktok_access_token,
                        "pinterest_access_token": pinterest_access_token,
                        "pinterest_board_id": pinterest_board_id,
                        "snapchat_access_token": snapchat_access_token,
                        "platforms": enabled_platforms,
                        "post_frequency": post_frequency
                    }
                    
                    # Update config
                    app["config"].update_config(config_dict)
                    app["config"].save_to_env()
                    
                    # Reconnect to platforms with improved feedback
                    with st.spinner("Updating configuration and reconnecting..."):
                        app["social_handler"].init_platform_clients()
                        # Clear platform status cache
                        get_cached_platform_status.clear()
                    
                    # Show success message outside the form
                    st.success("Configuration saved successfully!")
                    time.sleep(0.3)  # Shorter delay
                    st.rerun()
                    
                except Exception as e:
                    logger.error(f"Error saving configuration: {str(e)}")
                    st.error(f"Error saving configuration: {str(e)}")

def display_sidebar(app):
    """Display the sidebar navigation"""
    import streamlit as st

    # Create a container for the header to control rendering
    header_container = st.sidebar.container()

    # Use a custom styled header
    header_container.markdown("""
    <div style="text-align: center; padding: 10px; background: linear-gradient(90deg, #1E1E1E, #3D0000, #1E1E1E); border-radius: 5px; margin-bottom: 15px;">
        <h2 style="color: #FF4B4B; margin: 0; font-weight: bold; text-shadow: 1px 1px 2px #000000;">🤖 AdBot Marketing</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Show current user
    user = app["auth_manager"].get_current_user()
    if user:
        header_container.markdown(f"<div style='text-align: center; font-weight: bold; margin-bottom: 15px;'>Welcome, {user.get('name', 'User')}!</div>", unsafe_allow_html=True)
    
    # Main navigation header
    header_container.markdown("""
    <div style="background-color: #f0f2f6; padding: 8px; border-radius: 5px; margin-bottom: 10px;">
        <h3 style="margin: 0; color: #262730; font-size: 1.2em;">📱 Navigation</h3>
    </div>
    """, unsafe_allow_html=True)

    # Main pages
    pages = [
        {"name": "Dashboard", "icon": "📊", "id": "Dashboard"},
        {"name": "Products", "icon": "🏷️", "id": "Products"},
        {"name": "Create Ad", "icon": "📝", "id": "Create Ad"},
        {"name": "Schedule", "icon": "🗓️", "id": "Schedule Posts"},
        {"name": "Analytics", "icon": "📈", "id": "Analytics"},
        {"name": "Billing", "icon": "💳", "id": "Billing"},
        {"name": "Team", "icon": "👥", "id": "Team"},
        {"name": "Settings", "icon": "⚙️", "id": "Platform Setup"}
    ]

    # Labels with icons
    page_labels = [f"{page['icon']} {page['name']}" for page in pages]

    # Set default current page
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = pages[0]["id"]
        st.session_state["previous_page"] = None
        
    # Navigation change callback with optimization
    def on_nav_change():
        # Only record value if it actually changed
        if "sidebar_selection" not in st.session_state:
            return
            
        selected_label = st.session_state.sidebar_selection
        selected_page = next(page['id'] for page in pages if f"{page['icon']} {page['name']}" == selected_label)
        
        if selected_page != st.session_state["current_page"]:
            # Preload common data to make transition smoother
            company = app["auth_manager"].get_current_company()
            if company:
                preload_data(app, company["id"])
                
            # Update page state    
            st.session_state["previous_page"] = st.session_state["current_page"]
            st.session_state["current_page"] = selected_page
            st.session_state["page_changed"] = True
            st.session_state["page_change_time"] = time.time()

    # Map current page to index
    current_index = next((i for i, page in enumerate(pages) if page['id'] == st.session_state["current_page"]), 0)

    # Render radio with on_change callback
    st.sidebar.radio(
        label="",
        options=page_labels,
        index=current_index,
        key="sidebar_selection",
        on_change=on_nav_change
    )

    # Add a loading indicator during page transitions
    if st.session_state.get("page_changed", False):
        last_change_time = st.session_state.get("page_change_time", 0)
        if time.time() - last_change_time < 0.5:  # Only show for a short period
            with st.sidebar:
                st.markdown("Loading page...")
                
        st.session_state["page_changed"] = False
        st.rerun()

    # Separator
    st.sidebar.markdown("""
    <div style="border-top: 1px solid #e6e6e6; margin: 15px 0;"></div>
    """, unsafe_allow_html=True)

    # Create container for app info
    info_container = st.sidebar.container()

    # App info
    info_container.markdown(
        """
        <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
            <h4 style="margin-top: 0; color: #262730;">AdBot Marketing</h4>
            <p style="font-size: 0.9em; margin-bottom: 5px; color: #444;">AI-powered social media automation</p>
            <p style="font-size: 0.8em; color: #555; text-align: right;">v1.0.0</p>
        </div>
        """, 
        unsafe_allow_html=True
    )

    # Bottom separator
    st.sidebar.markdown("""
    <div style="border-top: 1px solid #e6e6e6; margin: 15px 0;"></div>
    """, unsafe_allow_html=True)

    # Logout button centered
    col1, col2, col3 = st.sidebar.columns([1, 2, 1])
    with col2:
        if st.button("🚪 Logout", key="logout_button", use_container_width=True):
            app["auth_manager"].logout()
            # Clear caches on logout
            for func in [get_cached_platform_status, get_cached_company_analytics, 
                         get_cached_company_balance, get_cached_company_schedules]:
                func.clear()
            st.rerun()


# Cache for page component state to avoid reinitialization
@st.cache_resource(ttl=300)
def get_page_cache():
    """Get or create page component cache"""
    return {}

def display_page(app, page):
    """Display the selected page with optimized loading"""
    
    # Get page cache
    page_cache = get_page_cache()
    
    # Create a placeholder for the page content
    if "page_placeholder" not in st.session_state:
        st.session_state.page_placeholder = st.empty()
    
    # Check if we're loading the same page as before
    same_page = st.session_state.get("previous_display_page") == page
    st.session_state["previous_display_page"] = page
    
    # Add a small progress indicator
    progress_bar = None
    if not same_page:
        progress_bar = st.progress(0)
        # Simulate quick progress to improve perceived performance
        for i in range(0, 101, 25):
            progress_bar.progress(i)
            time.sleep(0.01)  # Very short sleep for visual feedback
    
    try:
        with st.session_state.page_placeholder.container():
            # Load the page content - use a simpler approach to avoid potential errors
            # Don't check 'same_page' to ensure content always loads
            if page == "Home" or page == "Dashboard":
                dashboard_page(app)
            elif page == "Products":
                products_page(app["data_access"], app["auth_manager"])
            elif page == "Create Ad":
                create_ad_page(
                    app["data_access"], 
                    app["auth_manager"], 
                    app["content_generator"], 
                    app["social_handler"],
                    app["payment_manager"]
                )
            elif page == "Schedule Posts":
                schedule_page(
                    app["data_access"], 
                    app["auth_manager"], 
                    app["scheduler"],
                    app["payment_manager"]
                )
            elif page == "Analytics":
                analytics_page(
                    app["data_access"], 
                    app["auth_manager"],
                    app["payment_manager"]
                )
            elif page == "Billing":
                billing_page(
                    app["payment_manager"], 
                    app["auth_manager"]
                )

            elif page == "Team":
                team_management_page(
                    app["auth_manager"], 
                    app["data_access"]
                )

            elif page == "Platform Setup":
                platform_setup_page(app)
                
            else:
                st.error(f"Invalid page: {page}")
                logger.error(f"Invalid page: {page}")
                        
    except Exception as e:
        st.error(f"Error loading {page} page: {str(e)}")
        logger.error(f"Error rendering {page} page: {str(e)}")
        
        # Display some helpful content
        st.subheader("We encountered an error")
        st.markdown("This could be due to one of the following:")
        st.markdown("1. Missing or improper data configuration")
        st.markdown("2. Connectivity issues with external services")
        st.markdown("3. Incompatible data formats")
        
        # Add a retry button
        if st.button("Retry", key="retry_page_load"):
            # Clear cache for failed page
            if page in page_cache:
                del page_cache[page]
            st.rerun()
    finally:
        # Complete and hide progress bar if it exists
        if progress_bar is not None:
            progress_bar.progress(100)
            progress_bar.empty()


if __name__ == "__main__":
    main() 