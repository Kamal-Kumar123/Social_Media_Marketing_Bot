"""
Authentication module for the AdBot application.
Handles user authentication with Google OAuth and session management.
"""

import os
import json
import logging
import datetime
import streamlit as st
from streamlit.components.v1 import html
import requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
import firebase_admin
from firebase_admin import credentials, firestore

# Configure logging
logger = logging.getLogger("Auth")

# Initialize Firebase (for user storage)
def initialize_firebase():
    """Initialize Firebase connection if not already done"""
    if not firebase_admin._apps:
        try:
            firebase_cred_path = os.getenv("FIREBASE_CRED_PATH", "firebase-credentials.json")
            cred = credentials.Certificate(firebase_cred_path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase initialized successfully in AuthManager")
            return True
        except Exception as e:
            logger.error(f"Error initializing Firebase: {str(e)}")
            return False
    return True

class AuthManager:
    """Class for handling user authentication and session management"""
    
    def __init__(self):
        """Initialize the authentication manager"""
        # Google OAuth configuration
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501/callback")
        
        # Initialize Firebase
        self.firebase_initialized = initialize_firebase()
        
        # Create user session
        if "user" not in st.session_state:
            st.session_state["user"] = None
        if "company" not in st.session_state:
            st.session_state["company"] = None
        if "show_email_form" not in st.session_state:
            st.session_state["show_email_form"] = False
    
    def login_page(self):
        """Display the login page with Google Sign-In"""
        st.title("AdBot - Login")
        
        st.markdown(
            """
            ### Welcome to AdBot Marketing

            Sign in to manage your social media marketing campaigns across multiple platforms.
            """
        )
        
        # Check for query parameters (for OAuth callback)
        query_params = st.query_params
        
        if "code" in query_params:
            # Handle OAuth callback
            self._process_oauth_callback(query_params["code"])
        
        # Login options
        st.markdown("---")
        st.markdown("### Sign in with:")
        
        col1, col2 = st.columns(2)
        
        # Google login button
        with col1:
            if st.button("Google", key="google_login", use_container_width=True):
                if not self.client_id or self.client_id == "":
                    st.error("Google OAuth credentials not configured. Please add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to your .env file.")
                else:
                    self._initiate_google_auth()
        
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
                            st.rerun()
                        else:
                            st.error("Invalid email or password")
                    else:
                        st.error("Please enter both email and password")
        
        # Development note
        st.markdown("---")
        st.info("**Development Mode:** Email login with test@example.com / password will create a test account")
    
    def _initiate_google_auth(self):
        """Initiate Google OAuth flow"""
        # Set up Google OAuth parameters
        auth_url = "https://accounts.google.com/o/oauth2/auth"
        auth_params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "email profile",
            "prompt": "select_account"
        }
        
        # Construct the authorization URL
        auth_url = f"{auth_url}?{'&'.join([f'{k}={v}' for k, v in auth_params.items()])}"
        
        # Redirect to Google sign-in
        js = f"""
        <script>
        window.location.href = "{auth_url}";
        </script>
        """
        html(js, height=0)
        
        # Clear existing query parameters
        st.query_params.clear()
    
    def _process_oauth_callback(self, code):
        """Process the OAuth callback"""
        try:
            # Exchange code for tokens
            token_url = "https://oauth2.googleapis.com/token"
            token_params = {
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code"
            }
            
            response = requests.post(token_url, data=token_params)
            tokens = response.json()
            
            if "error" in tokens:
                st.error(f"Authentication error: {tokens['error']}")
                # Remove the query parameters to avoid repeated attempts
                st.query_params.clear()
                return
            
            # Get user info from ID token
            id_info = id_token.verify_oauth2_token(
                tokens["id_token"],
                google.auth.transport.requests.Request(),
                self.client_id
            )
            
            if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Invalid issuer')
            
            # Process user information
            user_data = {
                "id": id_info.get("sub"),
                "email": id_info.get("email"),
                "name": id_info.get("name"),
                "picture": id_info.get("picture"),
                "last_login": datetime.datetime.now().isoformat()
            }
            
            # Add or update user in database
            self._store_user(user_data)
            
            # Set user in session state
            st.session_state["user"] = user_data
            
            # Get or create company for user
            company = self._get_user_company(user_data["id"])
            st.session_state["company"] = company
            
            # Redirect to remove query parameters
            st.query_params.clear()
            st.rerun()
            
        except Exception as e:
            logger.error(f"Error processing OAuth callback: {str(e)}")
            st.error(f"Authentication failed: {str(e)}")
            st.query_params.clear()
    
    def _store_user(self, user_data):
        """Store user data in Firestore"""
        if not self.firebase_initialized:
            logger.error("Firebase not initialized, cannot store user")
            return False
        
        try:
            db = firestore.client()
            db.collection("users").document(user_data["id"]).set(user_data, merge=True)
            logger.info(f"User {user_data['email']} stored/updated in Firestore")
            return True
        except Exception as e:
            logger.error(f"Error storing user in Firestore: {str(e)}")
            return False
    
    def _get_user_company(self, user_id):
        """Get company data for a user"""
        if not self.firebase_initialized:
            logger.error("Firebase not initialized, cannot get user company")
            return None
        
        try:
            db = firestore.client()
            # Check if user is associated with any company
            company_memberships = db.collection("company_members").where("user_id", "==", user_id).get()
            
            if not company_memberships:
                # Create a default company for the user
                user = db.collection("users").document(user_id).get().to_dict()
                company_name = f"{user.get('name', 'Personal')}'s Workspace"
                
                # Create company
                new_company = {
                    "name": company_name,
                    "created_at": datetime.datetime.now().isoformat(),
                    "created_by": user_id,
                    "plan": "free"  # Default free plan
                }
                
                company_ref = db.collection("companies").add(new_company)
                company_id = company_ref[1].id
                
                # Add user as admin of the company
                db.collection("company_members").add({
                    "user_id": user_id,
                    "company_id": company_id,
                    "role": "admin",
                    "added_at": datetime.datetime.now().isoformat()
                })
                
                return {
                    "id": company_id,
                    **new_company
                }
            else:
                # Get first company the user is a member of
                first_membership = company_memberships[0].to_dict()
                company_id = first_membership.get("company_id")
                company = db.collection("companies").document(company_id).get().to_dict()
                
                return {
                    "id": company_id,
                    **company
                }
                
        except Exception as e:
            logger.error(f"Error getting user company: {str(e)}")
            return None
    
    def get_current_user(self):
        """Get the current user from the session"""
        return st.session_state.get("user")
    
    def get_current_company(self):
        """Get the current company from the session"""
        return st.session_state.get("company")
    
    def logout(self):
        """Log the user out and clear session"""
        st.session_state["user"] = None
        st.session_state["company"] = None
        st.rerun()
    
    def is_authenticated(self):
        """Check if user is authenticated"""
        return "user" in st.session_state and st.session_state.get("user") is not None
    
    def get_user_companies(self, user_id):
        """Get all companies a user is a member of"""
        if not self.firebase_initialized:
            logger.error("Firebase not initialized, cannot get user companies")
            return []
        
        try:
            db = firestore.client()
            memberships = db.collection("company_members").where("user_id", "==", user_id).get()
            
            companies = []
            for membership in memberships:
                membership_data = membership.to_dict()
                company_id = membership_data.get("company_id")
                company = db.collection("companies").document(company_id).get().to_dict()
                
                if company:
                    companies.append({
                        "id": company_id,
                        "role": membership_data.get("role", "member"),
                        **company
                    })
            
            return companies
        except Exception as e:
            logger.error(f"Error getting user companies: {str(e)}")
            return []
    
    def switch_company(self, company_id):
        """Switch to a different company"""
        if not self.firebase_initialized:
            logger.error("Firebase not initialized, cannot switch company")
            return False
        
        try:
            user_id = st.session_state.get("user", {}).get("id")
            if not user_id:
                return False
            
            db = firestore.client()
            membership = db.collection("company_members").where("user_id", "==", user_id).where("company_id", "==", company_id).get()
            
            if not membership:
                return False
            
            company = db.collection("companies").document(company_id).get().to_dict()
            if company:
                st.session_state["company"] = {
                    "id": company_id,
                    **company
                }
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error switching company: {str(e)}")
            return False
    
    def add_company_member(self, company_id, email, role="member"):
        """Add a new member to a company"""
        if not self.firebase_initialized:
            logger.error("Firebase not initialized, cannot add company member")
            return False
        
        try:
            # Verify current user is admin of the company
            user_id = st.session_state.get("user", {}).get("id")
            if not user_id:
                return "User not authenticated"
            
            db = firestore.client()
            admin_check = db.collection("company_members").where("user_id", "==", user_id).where("company_id", "==", company_id).where("role", "==", "admin").get()
            
            if not admin_check:
                return "Only administrators can add members"
            
            # Find user by email
            users = db.collection("users").where("email", "==", email).get()
            
            if not users:
                return f"User with email {email} not found"
            
            target_user_id = users[0].id
            
            # Check if user is already a member
            existing_membership = db.collection("company_members").where("user_id", "==", target_user_id).where("company_id", "==", company_id).get()
            
            if existing_membership:
                return f"User is already a member of this company"
            
            # Add user as member
            db.collection("company_members").add({
                "user_id": target_user_id,
                "company_id": company_id,
                "role": role,
                "added_at": datetime.datetime.now().isoformat(),
                "added_by": user_id
            })
            
            return "success"
        except Exception as e:
            logger.error(f"Error adding company member: {str(e)}")
            return f"Error: {str(e)}" 