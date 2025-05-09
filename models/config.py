"""
Configuration module for the AdBot application.
Handles loading and storing all API credentials and settings.
"""

import os
import json
import logging
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger("Config")

# Load environment variables
load_dotenv()

class Config:
    """Config class to manage all API credentials and settings"""
    
    def __init__(self):
        """Initialize configuration from environment variables"""
        # Log that we're initializing
        logger.info("Initializing configuration from environment variables")
        
        # API credentials
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # Social Media API Keys
        self.facebook_access_token = os.getenv("FACEBOOK_ACCESS_TOKEN")
        self.facebook_app_id = os.getenv("FACEBOOK_APP_ID")
        self.facebook_app_secret = os.getenv("FACEBOOK_APP_SECRET")
        self.facebook_page_id = os.getenv("FACEBOOK_PAGE_ID")
        
        self.twitter_api_key = os.getenv("TWITTER_API_KEY")
        self.twitter_api_secret = os.getenv("TWITTER_API_SECRET")
        self.twitter_access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        self.twitter_access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
        
        self.instagram_username = os.getenv("INSTAGRAM_USERNAME")
        self.instagram_password = os.getenv("INSTAGRAM_PASSWORD")
        
        self.linkedin_client_id = os.getenv("LINKEDIN_CLIENT_ID")
        self.linkedin_client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
        self.linkedin_access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        
        self.tiktok_access_token = os.getenv("TIKTOK_ACCESS_TOKEN")
        
        self.pinterest_access_token = os.getenv("PINTEREST_ACCESS_TOKEN")
        self.pinterest_board_id = os.getenv("PINTEREST_BOARD_ID")
        
        self.snapchat_access_token = os.getenv("SNAPCHAT_ACCESS_TOKEN")
        
        # Bot configuration
        self.campaign_data_path = os.getenv("CAMPAIGN_DATA_PATH", "data/campaigns.json")
        self.product_data_path = os.getenv("PRODUCT_DATA_PATH", "data/products.json")
        self.analytics_data_path = os.getenv("ANALYTICS_DATA_PATH", "data/analytics")

        #changeable
        self.post_frequency = int(os.getenv("POST_FREQUENCY", "8"))  # posts per day

        #changeable
        self.platforms = json.loads(os.getenv("PLATFORMS", '["facebook", "twitter", "instagram", "linkedin"]'))
        
        #changeable
        # Log API credential status (safely, without exposing actual values)
        logger.info(f"OpenAI API Key: {'Set' if self.openai_api_key else 'Not Set'}")
        logger.info(f"Twitter API Key: {'Set' if self.twitter_api_key else 'Not Set'}")
        logger.info(f"Twitter API Secret: {'Set' if self.twitter_api_secret else 'Not Set'}")
        logger.info(f"Twitter Access Token: {'Set' if self.twitter_access_token else 'Not Set'}")
        logger.info(f"Twitter Access Token Secret: {'Set' if self.twitter_access_token_secret else 'Not Set'}")
        logger.info(f"Facebook Access Token: {'Set' if self.facebook_access_token else 'Not Set'}")
        logger.info(f"Facebook App ID: {'Set' if self.facebook_app_id else 'Not Set'}")
        logger.info(f"Facebook App Secret: {'Set' if self.facebook_app_secret else 'Not Set'}")
        logger.info(f"Facebook Page ID: {'Set' if self.facebook_page_id else 'Not Set'}")
        logger.info(f"Instagram Username: {'Set' if self.instagram_username else 'Not Set'}")
        logger.info(f"Instagram Password: {'Set' if self.instagram_password else 'Not Set'}")
    
    def update_config(self, config_dict):
        """Update configuration with values from a dictionary"""
        # Update API keys
        if "openai_api_key" in config_dict:
            self.openai_api_key = config_dict["openai_api_key"]
            os.environ["OPENAI_API_KEY"] = config_dict["openai_api_key"]
        
        #changeable
        # Update social media credentials
        for platform in ["facebook", "twitter", "instagram", "linkedin", "tiktok", "pinterest", "snapchat"]:
            for key in config_dict:
                if key.startswith(f"{platform}_"):
                    setattr(self, key, config_dict[key])
                    os.environ[key.upper()] = config_dict[key]
        
        # Update bot configuration
        if "platforms" in config_dict:
            self.platforms = config_dict["platforms"]
            os.environ["PLATFORMS"] = json.dumps(config_dict["platforms"])
        
        if "post_frequency" in config_dict:
            self.post_frequency = int(config_dict["post_frequency"])
            os.environ["POST_FREQUENCY"] = str(config_dict["post_frequency"])
    
    def save_to_env(self):
        """Save current configuration to .env file"""
        env_vars = []
        
        # Add API keys
        env_vars.append(f"OPENAI_API_KEY={self.openai_api_key}")
        
        # Add social media credentials
        env_vars.append(f"FACEBOOK_ACCESS_TOKEN={self.facebook_access_token}")
        env_vars.append(f"FACEBOOK_APP_ID={self.facebook_app_id}")
        env_vars.append(f"FACEBOOK_APP_SECRET={self.facebook_app_secret}")
        env_vars.append(f"FACEBOOK_PAGE_ID={self.facebook_page_id}")
        
        env_vars.append(f"TWITTER_API_KEY={self.twitter_api_key}")
        env_vars.append(f"TWITTER_API_SECRET={self.twitter_api_secret}")
        env_vars.append(f"TWITTER_ACCESS_TOKEN={self.twitter_access_token}")
        env_vars.append(f"TWITTER_ACCESS_TOKEN_SECRET={self.twitter_access_token_secret}")
        
        env_vars.append(f"INSTAGRAM_USERNAME={self.instagram_username}")
        env_vars.append(f"INSTAGRAM_PASSWORD={self.instagram_password}")
        
        env_vars.append(f"LINKEDIN_CLIENT_ID={self.linkedin_client_id}")
        env_vars.append(f"LINKEDIN_CLIENT_SECRET={self.linkedin_client_secret}")
        env_vars.append(f"LINKEDIN_ACCESS_TOKEN={self.linkedin_access_token}")
        
        env_vars.append(f"TIKTOK_ACCESS_TOKEN={self.tiktok_access_token}")
        
        env_vars.append(f"PINTEREST_ACCESS_TOKEN={self.pinterest_access_token}")
        env_vars.append(f"PINTEREST_BOARD_ID={self.pinterest_board_id}")
        
        env_vars.append(f"SNAPCHAT_ACCESS_TOKEN={self.snapchat_access_token}")
        
        # Add bot configuration
        env_vars.append(f"CAMPAIGN_DATA_PATH={self.campaign_data_path}")
        env_vars.append(f"PRODUCT_DATA_PATH={self.product_data_path}")
        env_vars.append(f"ANALYTICS_DATA_PATH={self.analytics_data_path}")
        env_vars.append(f"POST_FREQUENCY={self.post_frequency}")
        env_vars.append(f"PLATFORMS={json.dumps(self.platforms)}")
        
        # Write to .env file
        with open(".env", "w") as f:
            f.write("\n".join(env_vars))
    
    def validate(self):
        """Validate that required configuration values are set"""
        missing_keys = []
        
        # Check for OpenAI API key
        if not self.openai_api_key:
            missing_keys.append("OPENAI_API_KEY")
        
        # Check for platform-specific keys based on enabled platforms
        if "facebook" in self.platforms:
            if not self.facebook_access_token:
                missing_keys.append("FACEBOOK_ACCESS_TOKEN")
            if not self.facebook_page_id:
                missing_keys.append("FACEBOOK_PAGE_ID")
        
        if "twitter" in self.platforms:
            if not self.twitter_api_key or not self.twitter_api_secret:
                missing_keys.append("TWITTER_API_KEY/SECRET")
            if not self.twitter_access_token or not self.twitter_access_token_secret:
                missing_keys.append("TWITTER_ACCESS_TOKEN/SECRET")
        
        if "instagram" in self.platforms:
            if not self.instagram_username or not self.instagram_password:
                missing_keys.append("INSTAGRAM_USERNAME/PASSWORD")
        
        if "linkedin" in self.platforms:
            if not self.linkedin_access_token:
                missing_keys.append("LINKEDIN_ACCESS_TOKEN")
        
        if "tiktok" in self.platforms:
            if not self.tiktok_access_token:
                missing_keys.append("TIKTOK_ACCESS_TOKEN")
        
        if "pinterest" in self.platforms:
            if not self.pinterest_access_token:
                missing_keys.append("PINTEREST_ACCESS_TOKEN")
            if not self.pinterest_board_id:
                missing_keys.append("PINTEREST_BOARD_ID")
        
        if "snapchat" in self.platforms:
            if not self.snapchat_access_token:
                missing_keys.append("SNAPCHAT_ACCESS_TOKEN")
        
        return missing_keys 