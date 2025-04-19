"""
Social Media Handler module for the AdBot application.
Handles integration with various social media platforms for posting content.
"""

import os
import logging
import datetime
import facebook  # Meta/Facebook API
import tweepy    # Twitter/X API
from linkedin_v2 import linkedin as linkedin
import instagrapi  # Instagram API
from TikTokApi import TikTokApi as tiktok  # TikTok API
from py3pin.Pinterest import Pinterest as pinterestapi  # Pinterest API
#from snapchat-dl as snapchat  # Snapchat API
from typing import Dict, List, Any, Optional, Union

# Configure logging
logger = logging.getLogger("SocialMediaHandler")

class SocialMediaHandler:
    """Class for handling social media platform integrations and posting"""
    
    def __init__(self, config):
        """Initialize the social media handler with the provided config"""
        self.config = config
        self.platforms = {}
        self.init_platform_clients()
    
    def init_platform_clients(self):
        """Initialize API clients for each platform"""
        try:
            # Validate platform credentials before initializing
            for platform in self.config.platforms:
                if platform == "facebook" and (not self.config.facebook_access_token or self.config.facebook_access_token == "your_facebook_access_token"):
                    logger.warning(f"Skipping {platform} initialization - missing or default credentials")
                    continue
                    
                if platform == "twitter" and (not self.config.twitter_api_key or self.config.twitter_api_key == "your_twitter_api_key"):
                    logger.warning(f"Skipping {platform} initialization - missing or default credentials")
                    continue
                    
                if platform == "instagram" and (not self.config.instagram_username or self.config.instagram_username == "your_instagram_username"):
                    logger.warning(f"Skipping {platform} initialization - missing or default credentials")
                    continue
                    
                if platform == "linkedin" and (not self.config.linkedin_client_id or self.config.linkedin_client_id == "your_linkedin_client_id"):
                    logger.warning(f"Skipping {platform} initialization - missing or default credentials")
                    continue
                    
                if platform == "tiktok" and (not self.config.tiktok_access_token or self.config.tiktok_access_token == "your_tiktok_access_token"):
                    logger.warning(f"Skipping {platform} initialization - missing or default credentials")
                    continue
                    
                if platform == "pinterest" and (not self.config.pinterest_access_token or self.config.pinterest_access_token == "your_pinterest_access_token"):
                    logger.warning(f"Skipping {platform} initialization - missing or default credentials")
                    continue
                    
                if platform == "snapchat" and (not self.config.snapchat_access_token or self.config.snapchat_access_token == "your_snapchat_access_token"):
                    logger.warning(f"Skipping {platform} initialization - missing or default credentials")
                    continue
            
                # Initialize specific platform clients only if credentials are valid
                if platform == "facebook":
                    try:
                        self.platforms["facebook"] = facebook.GraphAPI(access_token=self.config.facebook_access_token, version="3.1")
                        logger.info("Facebook API client initialized")
                    except Exception as e:
                        logger.error(f"Failed to initialize Facebook client: {str(e)}")
                    
                elif platform == "twitter":
                    try:
                        auth = tweepy.OAuth1UserHandler(
                            self.config.twitter_api_key, 
                            self.config.twitter_api_secret,
                            self.config.twitter_access_token, 
                            self.config.twitter_access_token_secret
                        )
                        self.platforms["twitter"] = tweepy.API(auth)
                        logger.info("Twitter API client initialized")
                    except Exception as e:
                        logger.error(f"Failed to initialize Twitter client: {str(e)}")
                    
                elif platform == "instagram":
                    try:
                        client = instagrapi.Client()
                        client.login(self.config.instagram_username, self.config.instagram_password)
                        self.platforms["instagram"] = client
                        logger.info("Instagram API client initialized")
                    except Exception as e:
                        logger.error(f"Failed to initialize Instagram client: {str(e)}")
                    
                elif platform == "linkedin":
                    try:
                        self.platforms["linkedin"] = linkedin.Linkedin(
                            self.config.linkedin_client_id,
                            self.config.linkedin_client_secret
                        )
                        self.platforms["linkedin"].authenticate_with_token(self.config.linkedin_access_token)
                        logger.info("LinkedIn API client initialized")
                    except Exception as e:
                        logger.error(f"Failed to initialize LinkedIn client: {str(e)}")
                    
                elif platform == "tiktok":
                    try:
                        self.platforms["tiktok"] = tiktok.TikTokAPI(self.config.tiktok_access_token)
                        logger.info("TikTok API client initialized")
                    except Exception as e:
                        logger.error(f"Failed to initialize TikTok client: {str(e)}")
                    
                elif platform == "pinterest":
                    try:
                        self.platforms["pinterest"] = pinterestapi(
                            email=self.config.pinterest_username,
                            password=self.config.pinterest_password,
                            username=self.config.pinterest_username,
                        )
                        logger.info("Pinterest API client initialized")
                    except Exception as e:
                        logger.error(f"Failed to initialize Pinterest client: {str(e)}")
                    
                elif platform == "snapchat":
                    try:
                        # Placeholder for Snapchat API
                        self.platforms["snapchat"] = {"client": "mock"}
                        logger.info("Snapchat API client initialized (mock)")
                    except Exception as e:
                        logger.error(f"Failed to initialize Snapchat client: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error initializing social media clients: {str(e)}")
    
    def post_to_facebook(self, ad_content: Dict) -> str:
        """Post ad to Facebook Page"""
        try:
            message = ad_content["copy"]
            image_path = ad_content.get("image_path")
            
            if image_path:
                with open(image_path, 'rb') as image_file:
                    response = self.platforms["facebook"].put_photo(
                        image=image_file,
                        message=message,
                        album_path=f"{self.config.facebook_page_id}/photos"
                    )
            else:
                response = self.platforms["facebook"].put_object(
                    parent_object=self.config.facebook_page_id,
                    connection_name="feed",
                    message=message
                )
            
            post_id = response.get("id")
            logger.info(f"Posted to Facebook, post_id: {post_id}")
            return post_id
            
        except Exception as e:
            logger.error(f"Error posting to Facebook: {str(e)}")
            return None
    
    def post_to_twitter(self, ad_content: Dict) -> str:
        """Post ad to Twitter/X"""
        try:
            text = ad_content["copy"]
            hashtags = ad_content.get("hashtags", [])
            
            # Add hashtags to the text
            if hashtags:
                hashtag_text = " ".join(hashtags)
                if len(text) + len(hashtag_text) + 1 <= 280:  # Twitter character limit
                    text = f"{text}\n{hashtag_text}"
                else:
                    # Truncate hashtags to fit character limit
                    available_chars = 280 - len(text) - 1
                    truncated_hashtags = []
                    current_length = 0
                    
                    for tag in hashtags:
                        if current_length + len(tag) + 1 <= available_chars:
                            truncated_hashtags.append(tag)
                            current_length += len(tag) + 1
                        else:
                            break
                    
                    if truncated_hashtags:
                        text = f"{text}\n{' '.join(truncated_hashtags)}"
            
            image_path = ad_content.get("image_path")
            
            if image_path:
                # Upload media and create tweet with media
                media = self.platforms["twitter"].media_upload(image_path)
                response = self.platforms["twitter"].update_status(
                    status=text,
                    media_ids=[media.media_id_string]
                )
            else:
                # Text-only tweet
                response = self.platforms["twitter"].update_status(text)
            
            tweet_id = response.id_str
            logger.info(f"Posted to Twitter, tweet_id: {tweet_id}")
            return tweet_id
            
        except Exception as e:
            logger.error(f"Error posting to Twitter: {str(e)}")
            return None
    
    def post_to_instagram(self, ad_content: Dict) -> str:
        """Post ad to Instagram"""
        try:
            caption = ad_content["copy"]
            image_path = ad_content.get("image_path")
            hashtags = ad_content.get("hashtags", [])
            
            # Add hashtags to caption
            if hashtags:
                caption = f"{caption}\n\n{' '.join(hashtags)}"
            
            if not image_path:
                logger.error("Instagram posts require an image")
                return None
            
            # Post to Instagram
            media = self.platforms["instagram"].photo_upload(
                image_path,
                caption=caption
            )
            
            media_id = media.id
            logger.info(f"Posted to Instagram, media_id: {media_id}")
            return media_id
            
        except Exception as e:
            logger.error(f"Error posting to Instagram: {str(e)}")
            return None
    
    def post_to_linkedin(self, ad_content: Dict) -> str:
        """Post ad to LinkedIn company page"""
        try:
            text = ad_content["copy"]
            image_path = ad_content.get("image_path")
            
            # Create post payload
            post_data = {
                "author": f"urn:li:organization:{self.config.linkedin_page_id}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": text
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            if image_path:
                # Upload image first
                with open(image_path, 'rb') as image_file:
                    image_data = image_file.read()
                
                upload_response = self.platforms["linkedin"].upload_image(image_data)
                
                if upload_response and "asset" in upload_response:
                    # Update post data to include the image
                    post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] = "IMAGE"
                    post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [
                        {
                            "status": "READY",
                            "media": upload_response["asset"],
                            "title": {
                                "text": ad_content["product_id"]
                            }
                        }
                    ]
            
            # Create the post
            response = self.platforms["linkedin"].create_post(post_data)
            
            post_id = response.get("id")
            logger.info(f"Posted to LinkedIn, post_id: {post_id}")
            return post_id
            
        except Exception as e:
            logger.error(f"Error posting to LinkedIn: {str(e)}")
            return None
    
    def post_to_tiktok(self, ad_content: Dict) -> str:
        """Post ad to TikTok"""
        try:
            caption = ad_content["copy"]
            image_path = ad_content.get("image_path")
            hashtags = ad_content.get("hashtags", [])
            
            # Add hashtags to caption
            if hashtags:
                caption = f"{caption} {' '.join(hashtags)}"
            
            if not image_path:
                logger.error("TikTok posts require an image or video")
                return None
            
            # For simplicity, we're assuming a static image here
            # In a real implementation, you'd need to create a video or use TikTok's Creation SDK
            response = self.platforms["tiktok"].upload_image(
                file_path=image_path,
                caption=caption
            )
            
            post_id = response.get("post_id")
            logger.info(f"Posted to TikTok, post_id: {post_id}")
            return post_id
            
        except Exception as e:
            logger.error(f"Error posting to TikTok: {str(e)}")
            return None
    
    def post_to_pinterest(self, ad_content: Dict) -> str:
        """Post ad to Pinterest as a Pin"""
        try:
            description = ad_content["copy"]
            image_path = ad_content.get("image_path")
            
            if not image_path:
                logger.error("Pinterest pins require an image")
                return None
            
            # For Pinterest, we need a board to pin to
            board_id = self.config.pinterest_board_id
            
            # Create pin
            response = self.platforms["pinterest"].create_pin(
                board_id=board_id,
                image_path=image_path,
                description=description,
                title=f"Ad for {ad_content['product_id']}"
            )
            
            pin_id = response.get("id")
            logger.info(f"Posted to Pinterest, pin_id: {pin_id}")
            return pin_id
            
        except Exception as e:
            logger.error(f"Error posting to Pinterest: {str(e)}")
            return None
    
    def post_to_snapchat(self, ad_content: Dict) -> str:
        """Post ad to Snapchat"""
        try:
            caption = ad_content["copy"]
            image_path = ad_content.get("image_path")
            
            if not image_path:
                logger.error("Snapchat posts require an image or video")
                return None
            
            # Post to Snapchat
            response = self.platforms["snapchat"].create_post(
                media_path=image_path,
                caption=caption
            )
            
            story_id = response.get("story_id")
            logger.info(f"Posted to Snapchat, story_id: {story_id}")
            return story_id
            
        except Exception as e:
            logger.error(f"Error posting to Snapchat: {str(e)}")
            return None
    
    def post_ad(self, ad_content: Dict) -> Dict:
        """Post an ad to the specified platforms"""
        platform = ad_content["platform"]
        result = {
            "success": False,
            "post_id": None,
            "platforms": {},
            "errors": []
        }
        
        try:
            if platform not in self.platforms:
                logger.error(f"Platform {platform} not configured")
                result["error"] = f"Platform {platform} not configured"
                return result
            
            # Call the appropriate method based on platform
            post_id = None
            if platform == "facebook":
                post_id = self.post_to_facebook(ad_content)
            elif platform == "twitter":
                post_id = self.post_to_twitter(ad_content)
            elif platform == "instagram":
                post_id = self.post_to_instagram(ad_content)
            elif platform == "linkedin":
                post_id = self.post_to_linkedin(ad_content)
            elif platform == "tiktok":
                post_id = self.post_to_tiktok(ad_content)
            elif platform == "pinterest":
                post_id = self.post_to_pinterest(ad_content)
            elif platform == "snapchat":
                post_id = self.post_to_snapchat(ad_content)
            
            if post_id:
                result["post_id"] = post_id
                result["success"] = True
            else:
                result["error"] = f"Failed to post to {platform}"
            
            return result
            
        except Exception as e:
            logger.error(f"Error posting ad to {platform}: {str(e)}")
            result["error"] = str(e)
            return result
    
    def get_platform_status(self) -> Dict:
        """Get the status of all configured platforms"""
        status = {}
        
        for platform in self.config.platforms:
            if platform in self.platforms:
                status[platform] = "connected"
            else:
                status[platform] = "not connected"
                
        return status 