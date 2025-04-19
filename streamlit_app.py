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

# Configure logging
logger = logging.getLogger("StreamlitApp")

# Import our models and utilities
from models import Config, ContentGenerator, SocialMediaHandler, AnalyticsManager
from utils import ProductManager, AdScheduler, AuthManager, PaymentManager, DataAccessManager
from page import (
    auth_pages, login_page, company_switcher, team_management_page, create_company_page,
    billing_page, products_page, create_ad_page, schedule_page, analytics_page
)

# Application state
@st.cache_resource
def initialize_app():
    """Initialize application components and return them"""
    # Create directories if they don't exist
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/images", exist_ok=True)
    os.makedirs("data/analytics", exist_ok=True)
    
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
        
    # Initialize authentication and data access after Firebase is initialized
    auth_manager = AuthManager()
    data_access = DataAccessManager()
    
    # Initialize components
    config = Config()
    content_generator = ContentGenerator(config)
    social_handler = SocialMediaHandler(config)
    analytics_manager = AnalyticsManager(config, social_handler)
    product_manager = ProductManager(config)
    scheduler = AdScheduler(config, product_manager, content_generator, social_handler, analytics_manager)
    payment_manager = PaymentManager()
    
    # Start the scheduler
    scheduler.start()
    
    return {
        "config": config,
        "content_generator": content_generator,
        "social_handler": social_handler,
        "analytics_manager": analytics_manager,
        "product_manager": product_manager,
        "scheduler": scheduler,
        "auth_manager": auth_manager,
        "data_access": data_access,
        "payment_manager": payment_manager
    }

def main():
    """Main application function"""
    st.set_page_config(
        page_title="AdBot - AI Marketing Assistant",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    try:
        # Add fancy banner at the top
        st.markdown("""
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
            
        # Check authentication
        if not app["auth_manager"].is_authenticated():
            auth_pages.login_page(app["auth_manager"])
            return
            
        # Setup sidebar
        auth_pages.company_switcher(app["auth_manager"])

        display_sidebar(app)
        
        # Display the current page
        page = st.session_state.get("current_page", "Home")
        display_page(app, page)
    except Exception as e:
        # Handle initialization errors
        st.error(f"An error occurred: {str(e)}")
        st.write("If this is related to Firebase, make sure your credentials file is properly set up.")
        
        # Create a simple login button
        if st.button("Try Again"):
            st.rerun()

def dashboard_page(app):
    """Dashboard page showing key metrics and status"""
    st.title("AdBot Dashboard")
    st.markdown("### AI-Powered Social Media Marketing Bot")
    
    # Get current user and company
    user = app["auth_manager"].get_current_user()
    company = app["auth_manager"].get_current_company()
    
    if not user or not company:
        st.warning("Please select a company to continue.")
        return
    
    # Welcome message
    st.markdown(f"## Welcome, {user.get('name', 'User')}!")
    st.markdown(f"**Current Workspace:** {company.get('name', 'Unknown')}")
    
    # Get platform connection status
    platform_status = app["social_handler"].get_platform_status()
    
    # Get company plan
    plan = company.get("plan", "free")
    plan_details = app["payment_manager"].plans.get(plan, {})
    
    # Show plan information
    st.markdown(f"**Current Plan:** {plan_details.get('name', plan.capitalize())}")
    
    # Analytics summary
    try:
        # Get company analytics
        analytics = app["data_access"].get_company_analytics(company["id"], 30)
        
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
            # Get credit balance
            balance = app["payment_manager"]._get_company_balance(company["id"])
            credit_balance = balance.get("balance", 0)
            
            st.metric(
                label="Credit Balance", 
                value=f"${credit_balance:.2f}"
            )
        
        with col4:
            # Scheduled posts
            schedules = app["data_access"].get_company_schedules(company["id"])
            scheduled_posts = len([s for s_id, s in schedules.items() if s.get("status") == "scheduled"])
            
            st.metric(
                label="Scheduled Posts", 
                value=scheduled_posts
            )
        
        # Quick Actions
        st.markdown("### Quick Actions")
        
        quick_col1, quick_col2, quick_col3, quick_col4 = st.columns(4)
        
        with quick_col1:
            if st.button("Create New Ad", key="dashboard_create_ad"):
                st.session_state["current_page"] = "Create Ad"
                st.rerun()
        
        with quick_col2:
            if st.button("Schedule Posts", key="dashboard_schedule"):
                st.session_state["current_page"] = "Schedule Posts"
                st.rerun()
        
        with quick_col3:
            if st.button("View Analytics", key="dashboard_analytics"):
                st.session_state["current_page"] = "Analytics"
                st.rerun()
        
        with quick_col4:
            if st.button("Add Credits", key="dashboard_add_credits"):
                st.session_state["current_page"] = "Billing"
                st.rerun()
        
        # Platform engagement if there's data
        if analytics.get("total_posts", 0) > 0:
            st.markdown("### Platform Performance")
            
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
                st.bar_chart(df.set_index("Platform")["Avg Engagement"])
        
        # Recent activity
        st.markdown("### Recent Activity")
        
        # Get recent posts
        recent_posts_ref = app["data_access"].db.collection("posts").where(
            "company_id", "==", company["id"]
        ).order_by("timestamp", direction="DESCENDING").limit(5).get()
        
        if recent_posts_ref:
            for post in recent_posts_ref:
                post_data = post.to_dict()
                platform = post_data.get("platform", "Unknown")
                product_id = post_data.get("product_id", "Unknown")
                
                # Get product name
                product = app["data_access"].get_product(product_id, company["id"])
                product_name = product.get("name", product_id) if product else product_id
                
                post_time = post_data.get("timestamp", "").split("T")[0] if isinstance(post_data.get("timestamp"), str) else "Unknown"
                
                st.write(f"🟢 **{platform.title()}** post for **{product_name}** on {post_time}")
        else:
            st.info("No recent activity. Create some posts to get started!")
        
    except Exception as e:
        logger.error(f"Error in dashboard: {str(e)}")
        st.error(f"Error loading dashboard data: {str(e)}")

import streamlit as st
import pandas as pd
import time

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
        
        # Get platform connection status
        platform_status = app["social_handler"].get_platform_status()
        
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
        st.table(status_df)
        
        # Initialize platforms
        if st.button("Refresh Platform Connections"):
            app["social_handler"].init_platform_clients()
            st.success("Platform connections refreshed!")
            time.sleep(1)
            st.rerun()

    
    with tab2:
        st.markdown("### API Configuration")
        
        with st.form("api_config_form"):
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
                    
                    # Reconnect to platforms
                    app["social_handler"].init_platform_clients()
                    
                    st.success("Configuration saved successfully!")
                    
                except Exception as e:
                    logger.error(f"Error saving configuration: {str(e)}")
                    st.error(f"Error saving configuration: {str(e)}")

def display_sidebar(app):
    """Display the sidebar navigation"""
    import streamlit as st

    # Use a custom styled header
    st.sidebar.markdown("""
    <div style="text-align: center; padding: 10px; background: linear-gradient(90deg, #1E1E1E, #3D0000, #1E1E1E); border-radius: 5px; margin-bottom: 15px;">
        <h2 style="color: #FF4B4B; margin: 0; font-weight: bold; text-shadow: 1px 1px 2px #000000;">🤖 AdBot Marketing</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Show current user
    user = app["auth_manager"].get_current_user()
    if user:
        st.sidebar.markdown(f"<div style='text-align: center; font-weight: bold; margin-bottom: 15px;'>Welcome, {user.get('name', 'User')}!</div>", unsafe_allow_html=True)
    
    # Main navigation header
    st.sidebar.markdown("""
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

    # Map current page to index
    current_index = next((i for i, page in enumerate(pages) if page['id'] == st.session_state["current_page"]), 0)

    # Render radio with key
    selected_label = st.sidebar.radio(
        label="",
        options=page_labels,
        index=current_index,
        key="sidebar_selection"
    )

    # Determine selected page
    selected_page = next(page['id'] for page in pages if f"{page['icon']} {page['name']}" == selected_label)

    # Update and rerun if changed
    if selected_page != st.session_state["current_page"]:
        st.session_state["current_page"] = selected_page
        st.rerun()

    # Separator
    st.sidebar.markdown("""
    <div style="border-top: 1px solid #e6e6e6; margin: 15px 0;"></div>
    """, unsafe_allow_html=True)

    # App info
    st.sidebar.markdown(
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
            st.rerun()


def display_page(app, page):
    """Display the selected page"""
    
    try:
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
        if st.button("Retry"):
            st.rerun()


if __name__ == "__main__":
    main() 