"""
Test script for Google OAuth integration
Run with: streamlit run test_google_auth.py
"""

import os
import streamlit as st
from utils.auth import AuthManager

# Setup page config
st.set_page_config(
    page_title="Google OAuth Test",
    page_icon="🔒",
    layout="centered"
)

# Create test UI
st.title("Google OAuth Test")
st.write("This is a simple test for Google OAuth integration")

# Initialize auth manager
auth_manager = AuthManager()

# Show current environment settings
st.subheader("Current OAuth Configuration")
client_id = os.getenv("GOOGLE_CLIENT_ID", "Not set")
client_secret_status = "Set" if os.getenv("GOOGLE_CLIENT_SECRET") else "Not set"
redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501/callback")

# Display masked client ID
masked_id = "Not set"
if client_id != "Not set":
    masked_id = client_id[:5] + "..." + client_id[-5:] if len(client_id) > 10 else client_id

st.write(f"Client ID: {masked_id}")
st.write(f"Client Secret: {client_secret_status}")
st.write(f"Redirect URI: {redirect_uri}")

# Test OAuth flow
st.subheader("Test Google OAuth")

# Check for callback query parameter
query_params = st.query_params
if "code" in query_params:
    with st.spinner("Processing OAuth callback..."):
        result = auth_manager._process_oauth_callback(query_params["code"])
        if result:
            st.success("Authentication successful!")
            
            # Show authenticated user
            user = auth_manager.get_current_user()
            if user:
                st.write("Authenticated User:")
                st.json(user)
            
            # Clear query params (doesn't work in Streamlit yet)
            st.button("Clear Query Parameters", on_click=lambda: st.query_params.clear())
        else:
            st.error("Authentication failed. Check logs for details.")
else:
    if st.button("Test Google Sign-In"):
        auth_manager._initiate_google_auth()

# Debugging info
st.subheader("Debug Information")
if "user" in st.session_state:
    st.write("User in session:", st.session_state.get("user") is not None)
else:
    st.write("No user in session")

# Instructions
st.markdown("""
### Setup Instructions:
1. Make sure your Google Cloud Project has OAuth credentials configured
2. Set the following environment variables:
   - `GOOGLE_CLIENT_ID`: Your Google OAuth client ID
   - `GOOGLE_CLIENT_SECRET`: Your Google OAuth client secret
   - `GOOGLE_REDIRECT_URI`: Must match the authorized redirect URI in Google Cloud (default: http://localhost:8501/callback)
3. Add the redirect URI to the authorized redirect URIs in your Google Cloud OAuth credentials
""") 