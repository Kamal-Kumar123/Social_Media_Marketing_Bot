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
    """Manages authentication for the application"""
    
    def __init__(self):
        """Initialize authentication manager"""
        # Load environment variables with fallbacks
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501/callback")

        
        # Log authentication configuration (without sensitive details)
        logger.info(f"AuthManager initialized with redirect URI: {self.redirect_uri}")
        if not self.client_id or not self.client_secret:
            logger.warning("Google OAuth credentials are not configured properly")
        
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
        if not self.client_id or not self.client_secret:
            st.error("Google OAuth credentials not configured.")
            logger.error("Attempted Google authentication with missing credentials")
            return
        
        try:
            # Generate authentication URL with clearer parameters
            auth_url = (
                "https://accounts.google.com/o/oauth2/auth?"
                f"client_id={self.client_id}&"
                f"redirect_uri={self.redirect_uri}&"
                "response_type=code&"
                "scope=email+profile&"
                "access_type=offline&"
                "prompt=select_account"
            )
            
            logger.info(f"Initiating Google OAuth flow with redirect to: {self.redirect_uri}")
            
            # Use JavaScript to redirect instead of streamlit's method
            # This avoids client-side redirect issues
            js_code = f"""
        <script>
            // Save the current page to session storage before redirecting
            sessionStorage.setItem('streamlit_oauth_redirect', 'true');
            // Redirect to Google Auth
        window.location.href = "{auth_url}";
        </script>
        """
            
            # Use Streamlit's HTML component to execute the JavaScript
            html(js_code, height=0)
        except Exception as e:
            logger.error(f"Error during Google authentication initiation: {str(e)}")
            st.error(f"Authentication error: {str(e)}")
    
    def _process_oauth_callback(self, code):
        """Process OAuth callback with authorization code"""
        if not code:
            logger.warning("OAuth callback received without authorization code")
            return False
        
        try:
            logger.info("Processing OAuth callback")
            
            # Exchange authorization code for tokens
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code"
            }
            
            token_response = requests.post(token_url, data=token_data)
            token_response.raise_for_status()
            token_info = token_response.json()
            
            # Get user information using the access token
            user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            headers = {"Authorization": f"Bearer {token_info['access_token']}"}
            user_response = requests.get(user_info_url, headers=headers)
            user_response.raise_for_status()
            user_info = user_response.json()
            
            # Create user object
            user = {
                "id": user_info["id"],
                "email": user_info["email"],
                "name": user_info.get("name", user_info["email"].split("@")[0]),
                "picture": user_info.get("picture", f"https://ui-avatars.com/api/?name={user_info.get('name', 'User')}&background=random")
            }
            
            # Store user in session
            st.session_state["user"] = user
            
            # Store user in Firestore if Firebase is initialized
            if self.firebase_initialized:
                self._store_user(user)
            
            # Create default company for the user if needed
            # You would typically check your database here
            # For demo purposes, we'll create a simple company
            test_company = {
                "id": f"{user['id']}-company",
                "name": f"{user['name']}'s Company",
                "owner": user['id'],
                "role": "owner",
                "plan": "free",
                "balance": 100.0,
                "members": [
                    {"id": user['id'], "email": user['email'], "role": "owner"}
                ]
            }
            
            # Store company in session
            st.session_state["company"] = test_company
            
            logger.info(f"Successfully authenticated user: {user['email']}")
            return True
            
        except Exception as e:
            logger.error(f"OAuth error: {str(e)}")
            st.error(f"Authentication error: {str(e)}")
            return False
    
    def _create_test_user(self):
        """Create a test user for development purposes"""
        try:
            # Create a simple test user
            test_user = {
                "id": "test-user-id",
                "email": "test@example.com",
                "name": "Test User",
                "picture": "https://ui-avatars.com/api/?name=Test+User&background=random",
                "last_login": datetime.datetime.now().isoformat()
            }
            
            # Store user in session
            st.session_state["user"] = test_user
            
            # Store user in Firestore if Firebase is initialized
            if self.firebase_initialized:
                self._store_user(test_user)
            
            # Create a test company for the user
            test_company = {
                "id": "test-company-id",
                "name": "Test Company",
                "description": "Company for development testing",
                "created_at": datetime.datetime.now().isoformat(),
                "created_by": "test-user-id",
                "plan": "free"  # Default free plan
            }
            
            # Store company in session
            st.session_state["company"] = test_company
            
            # Store company in Firestore if Firebase is initialized
            if self.firebase_initialized:
                db = firestore.client()
                # Check if test company exists
                company_ref = db.collection("companies").document("test-company-id")
                if not company_ref.get().exists:
                    company_ref.set(test_company)
                    # Add user as admin of the company
                    db.collection("company_members").add({
                        "user_id": "test-user-id",
                        "company_id": "test-company-id",
                        "role": "admin",
                        "added_at": datetime.datetime.now().isoformat()
                    })
            
            return True
        except Exception as e:
            logger.error(f"Error creating test user: {str(e)}")
            return False
    
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
        """Get current user"""
        if self.is_authenticated():
            return st.session_state["user"]
        return None
    
    def get_current_company(self):
        """Get current company"""
        if "company" in st.session_state:
            return st.session_state["company"]
        return None
    
    def logout(self):
        """Log user out"""
        if "user" in st.session_state:
            del st.session_state["user"]
        if "company" in st.session_state:
            del st.session_state["company"]
    
    def is_authenticated(self):
        """Check if user is authenticated"""
        return "user" in st.session_state and st.session_state["user"] is not None
    
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