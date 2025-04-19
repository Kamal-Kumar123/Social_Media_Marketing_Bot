# Social Media Marketing Bot
# A comprehensive bot for automated ad posting across multiple social media platforms

import os
import time
import json
import logging
import schedule
import requests
import datetime
import pandas as pd
import openai
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional, Union

# For image processing
from PIL import Image
import io

# For social media APIs
import facebook  # Meta/Facebook API
import tweepy    # Twitter/X API
import linkedin.api as linkedin
import instagrapi  # Instagram API
import tiktok_api as tiktok  # TikTok API
import pinterestapi  # Pinterest API
import snapchat_api as snapchat  # Snapchat API

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("marketing_bot.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("MarketingBot")

# API Keys and Configuration
class Config:
    def __init__(self):
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
        self.snapchat_access_token = os.getenv("SNAPCHAT_ACCESS_TOKEN")
        
        # Bot configuration
        self.campaign_data_path = os.getenv("CAMPAIGN_DATA_PATH", "data/campaigns.json")
        self.product_data_path = os.getenv("PRODUCT_DATA_PATH", "data/products.json")
        self.analytics_data_path = os.getenv("ANALYTICS_DATA_PATH", "data/analytics")
        self.post_frequency = int(os.getenv("POST_FREQUENCY", "8"))  # posts per day
        self.platforms = json.loads(os.getenv("PLATFORMS", '["facebook", "twitter", "instagram", "linkedin"]'))

# Ad Content Generator using OpenAI
class ContentGenerator:
    def __init__(self, config: Config):
        self.config = config
        openai.api_key = config.openai_api_key
    
    def generate_ad_copy(self, product: Dict, platform: str, tone: str, length: str) -> str:
        """Generate ad copy based on product information and platform requirements"""
        try:
            # Different character limits and styles for each platform
            platform_guidelines = {
                "facebook": "Up to 125 characters for headline, 30-90 words for body text.",
                "twitter": "280 character limit. Concise and engaging.",
                "instagram": "Caption up to 2200 characters, first 125 visible without tapping more.",
                "linkedin": "Professional tone, up to 700 characters for best visibility.",
                "tiktok": "Short, catchy caption that drives engagement.",
                "pinterest": "Clear description with relevant keywords.",
                "snapchat": "Brief and casual, call-to-action focused."
            }
            
            length_guide = {
                "short": "2-3 sentences",
                "medium": "4-5 sentences",
                "long": "6-8 sentences"
            }
            
            # Construct the prompt
            prompt = f"""
            Create an engaging {platform} ad for the following product:
            
            Product Name: {product['name']}
            Description: {product['description']}
            Key Features: {', '.join(product['features'])}
            Target Audience: {product['target_audience']}
            
            Platform Guidelines: {platform_guidelines.get(platform, '')}
            Length: {length_guide.get(length, 'medium')}
            Tone: {tone}
            
            Include a compelling call-to-action.
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert marketing copywriter specializing in social media ads."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            ad_copy = response.choices[0].message.content.strip()
            logger.info(f"Generated ad copy for {product['name']} on {platform}")
            
            return ad_copy
            
        except Exception as e:
            logger.error(f"Error generating ad copy: {str(e)}")
            return f"Check out our amazing {product['name']}! {' '.join(product['features'][:2])}. Learn more now!"
    
    def generate_image_prompt(self, product: Dict, platform: str, style: str) -> str:
        """Generate a prompt for image creation based on product details"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert in creating detailed image generation prompts for marketing."},
                    {"role": "user", "content": f"""
                    Create a detailed image generation prompt for a product ad. The prompt should be suitable for DALL-E or Midjourney.
                    
                    Product: {product['name']}
                    Description: {product['description']}
                    Target Platform: {platform}
                    Style Preference: {style}
                    Target Audience: {product['target_audience']}
                    
                    The image should be engaging and highlight the product's key features.
                    """}
                ],
                max_tokens=100,
                temperature=0.7
            )
            
            image_prompt = response.choices[0].message.content.strip()
            logger.info(f"Generated image prompt for {product['name']}")
            
            return image_prompt
            
        except Exception as e:
            logger.error(f"Error generating image prompt: {str(e)}")
            return f"Professional photo of {product['name']} in {style} style, appealing to {product['target_audience']}"
    
    def generate_image(self, prompt: str, size: str = "1024x1024") -> bytes:
        """Generate an image using DALL-E based on the prompt"""
        try:
            response = openai.Image.create(
                prompt=prompt,
                n=1,
                size=size
            )
            
            # Download the image
            image_url = response['data'][0]['url']
            image_response = requests.get(image_url)
            
            if image_response.status_code == 200:
                logger.info("Successfully generated image")
                return image_response.content
            else:
                logger.error(f"Failed to download generated image: {image_response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            return None
    
    def create_ad_content(self, product: Dict, platform: str, format_type: str = "image") -> Dict:
        """Create complete ad content including text and visual elements"""
        ad_content = {
            "product_id": product["id"],
            "platform": platform,
            "created_at": datetime.datetime.now().isoformat(),
            "type": format_type
        }
        
        # Generate ad copy based on platform
        tone = "professional" if platform == "linkedin" else "conversational"
        length = "medium"
        
        ad_content["copy"] = self.generate_ad_copy(product, platform, tone, length)
        
        # Generate visual content if needed
        if format_type == "image":
            style = "clean, professional" if platform == "linkedin" else "vibrant, eye-catching"
            image_prompt = self.generate_image_prompt(product, platform, style)
            image_bytes = self.generate_image(image_prompt)
            
            if image_bytes:
                # Save image to file
                timestamp = int(time.time())
                image_path = f"data/images/{product['id']}{platform}{timestamp}.png"
                os.makedirs(os.path.dirname(image_path), exist_ok=True)
                
                with open(image_path, "wb") as img_file:
                    img_file.write(image_bytes)
                
                ad_content["image_path"] = image_path
        
        # Add hashtags for appropriate platforms
        if platform in ["instagram", "twitter", "tiktok"]:
            ad_content["hashtags"] = self.generate_hashtags(product, platform)
        
        return ad_content
    
    def generate_hashtags(self, product: Dict, platform: str) -> List[str]:
        """Generate relevant hashtags for the product and platform"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a social media marketing expert specializing in hashtag optimization."},
                    {"role": "user", "content": f"""
                    Generate 5-7 relevant and trending hashtags for this product on {platform}:
                    
                    Product: {product['name']}
                    Category: {product.get('category', 'General')}
                    Target Audience: {product['target_audience']}
                    
                    Include a mix of popular and niche hashtags for maximum reach.
                    Return only the hashtags without any explanation, separated by commas.
                    """}
                ],
                max_tokens=100,
                temperature=0.7
            )
            
            hashtags = [tag.strip() for tag in response.choices[0].message.content.split(',')]
            hashtags = [tag if tag.startswith('#') else f"#{tag}" for tag in hashtags]
            
            return hashtags
            
        except Exception as e:
            logger.error(f"Error generating hashtags: {str(e)}")
            return [f"#{product['name'].replace(' ', '')}", "#newproduct", "#musthave"]

# Social Media Platform Handler
class SocialMediaHandler:
    def __init__(self, config: Config):
        self.config = config
        self.platforms = {}
        self.init_platform_clients()
    
    def init_platform_clients(self):
        """Initialize API clients for each platform"""
        try:
            # Facebook/Meta API
            if "facebook" in self.config.platforms:
                self.platforms["facebook"] = facebook.GraphAPI(access_token=self.config.facebook_access_token, version="12.0")
                logger.info("Facebook API client initialized")
            
            # Twitter/X API
            if "twitter" in self.config.platforms:
                auth = tweepy.OAuth1UserHandler(
                    self.config.twitter_api_key, 
                    self.config.twitter_api_secret,
                    self.config.twitter_access_token, 
                    self.config.twitter_access_token_secret
                )
                self.platforms["twitter"] = tweepy.API(auth)
                logger.info("Twitter API client initialized")
            
            # Instagram API
            if "instagram" in self.config.platforms:
                client = instagrapi.Client()
                client.login(self.config.instagram_username, self.config.instagram_password)
                self.platforms["instagram"] = client
                logger.info("Instagram API client initialized")
            
            # LinkedIn API
            if "linkedin" in self.config.platforms:
                self.platforms["linkedin"] = linkedin.Linkedin(
                    self.config.linkedin_client_id,
                    self.config.linkedin_client_secret
                )
                self.platforms["linkedin"].authenticate_with_token(self.config.linkedin_access_token)
                logger.info("LinkedIn API client initialized")
            
            # TikTok API
            if "tiktok" in self.config.platforms:
                self.platforms["tiktok"] = tiktok.TikTokAPI(self.config.tiktok_access_token)
                logger.info("TikTok API client initialized")
            
            # Pinterest API
            if "pinterest" in self.config.platforms:
                self.platforms["pinterest"] = pinterestapi.PinterestAPI(self.config.pinterest_access_token)
                logger.info("Pinterest API client initialized")
            
            # Snapchat API
            if "snapchat" in self.config.platforms:
                self.platforms["snapchat"] = snapchat.SnapchatAPI(self.config.snapchat_access_token)
                logger.info("Snapchat API client initialized")
            
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
        """Post an ad to the specified platform and return results"""
        platform = ad_content["platform"]
        result = {
            "platform": platform,
            "product_id": ad_content["product_id"],
            "timestamp": datetime.datetime.now().isoformat(),
            "success": False
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

# Analytics and Optimization
class AnalyticsManager:
    def __init__(self, config: Config, social_handler: SocialMediaHandler):
        self.config = config
        self.social_handler = social_handler
        self.analytics_data = {}
        self.load_analytics_data()
    
    def load_analytics_data(self):
        """Load existing analytics data from file"""
        analytics_file = f"{self.config.analytics_data_path}/analytics_data.json"
        os.makedirs(os.path.dirname(analytics_file), exist_ok=True)
        
        if os.path.exists(analytics_file):
            try:
                with open(analytics_file, 'r') as f:
                    self.analytics_data = json.load(f)
                logger.info("Loaded analytics data")
            except Exception as e:
                logger.error(f"Error loading analytics data: {str(e)}")
                self.analytics_data = {}
        else:
            self.analytics_data = {}
    
    def save_analytics_data(self):
        """Save analytics data to file"""
        analytics_file = f"{self.config.analytics_data_path}/analytics_data.json"
        os.makedirs(os.path.dirname(analytics_file), exist_ok=True)
        
        try:
            with open(analytics_file, 'w') as f:
                json.dump(self.analytics_data, f, indent=2)
            logger.info("Saved analytics data")
        except Exception as e:
            logger.error(f"Error saving analytics data: {str(e)}")
    
    def collect_metrics(self, post_result: Dict) -> Dict:
        """Collect engagement metrics for a posted ad"""
        if not post_result["success"]:
            return None
        
        platform = post_result["platform"]
        post_id = post_result["post_id"]
        metrics = {
            "post_id": post_id,
            "platform": platform,
            "product_id": post_result["product_id"],
            "timestamp": datetime.datetime.now().isoformat(),
            "engagement": {}
        }
        
        try:
            if platform == "facebook":
                # Get metrics from Facebook
                insights = self.social_handler.platforms["facebook"].get_object(
                    id=post_id,
                    fields="insights.metric(post_impressions,post_engagements,post_reactions_by_type)"
                )
                
                if "insights" in insights and "data" in insights["insights"]:
                    for data in insights["insights"]["data"]:
                        metric_name = data["name"]
                        if "values" in data and len(data["values"]) > 0:
                            metrics["engagement"][metric_name] = data["values"][0]["value"]
            
            elif platform == "twitter":
                # Get metrics from Twitter
                tweet = self.social_handler.platforms["twitter"].get_status(post_id, tweet_mode="extended")
                metrics["engagement"] = {
                    "retweets": tweet.retweet_count,
                    "likes": tweet.favorite_count,
                    "replies": 0  # Need additional API call to get reply count
                }
            
            elif platform == "instagram":
                # Get metrics from Instagram
                media_info = self.social_handler.platforms["instagram"].media_info(post_id)
                metrics["engagement"] = {
                    "likes": media_info.like_count,
                    "comments": media_info.comment_count,
                    "saves": 0  # Not directly available
                }
            
            elif platform == "linkedin":
                # Get metrics from LinkedIn
                stats = self.social_handler.platforms["linkedin"].get_post_stats(post_id)
                metrics["engagement"] = {
                    "impressions": stats.get("totalShares", 0),
                    "clicks": stats.get("clicks", 0),
                    "likes": stats.get("likes", 0),
                    "comments": stats.get("comments", 0)
                }
            
            # Add more platforms as needed
            
            # Store metrics in analytics data
            if post_id not in self.analytics_data:
                self.analytics_data[post_id] = []
            
            self.analytics_data[post_id].append(metrics)
            self.save_analytics_data()
            
            logger.info(f"Collected metrics for post {post_id} on {platform}")
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting metrics for post {post_id} on {platform}: {str(e)}")
            return None
    
    def analyze_performance(self, product_id: str = None, platform: str = None, days: int = 30) -> Dict:
        """Analyze ad performance for optimization"""
        try:
            # Filter metrics based on parameters
            filtered_data = []
            current_time = datetime.datetime.now()
            cutoff_time = current_time - datetime.timedelta(days=days)
            
            for post_id, metrics_list in self.analytics_data.items():
                for metrics in metrics_list:
                    # Check if metrics match the filters
                    if product_id and metrics["product_id"] != product_id:
                        continue
                    
                    if platform and metrics["platform"] != platform:
                        continue
                    
                    # Check if within time range
                    metrics_time = datetime.datetime.fromisoformat(metrics["timestamp"])
                    if metrics_time < cutoff_time:
                        continue
                    
                    filtered_data.append(metrics)
            
            # Group and analyze data
            platform_performance = {}
            product_performance = {}
            
            for metrics in filtered_data:
                platform = metrics["platform"]
                product_id = metrics["product_id"]
                
                # Initialize if not exists
                if platform not in platform_performance:
                    platform_performance[platform] = {
                        "post_count": 0,
                        "engagement": {},
                        "posts": []
                    }
                
                if product_id not in product_performance:
                    product_performance[product_id] = {
                        "post_count": 0,
                        "platform_performance": {},
                        "posts": []
                    }
                
                # Update platform performance
                platform_performance[platform]["post_count"] += 1
                platform_performance[platform]["posts"].append(metrics["post_id"])
                
                # Update product performance
                product_performance[product_id]["post_count"] += 1
                
                if platform not in product_performance[product_id]["platform_performance"]:
                    product_performance[product_id]["platform_performance"][platform] = {
                        "post_count": 0,
                        "engagement": {},
                        "posts": []
                    }
                
                product_performance[product_id]["platform_performance"][platform]["post_count"] += 1
                product_performance[product_id]["platform_performance"][platform]["posts"].append(metrics["post_id"])
                
                # Aggregate engagement metrics
                for metric, value in metrics.get("engagement", {}).items():
                    # For platform performance
                    if metric not in platform_performance[platform]["engagement"]:
                        platform_performance[platform]["engagement"][metric] = 0
                    platform_performance[platform]["engagement"][metric] += value
                    
                    # For product performance
                    if metric not in product_performance[product_id]["platform_performance"][platform]["engagement"]:
                        product_performance[product_id]["platform_performance"][platform]["engagement"][metric] = 0
                    product_performance[product_id]["platform_performance"][platform]["engagement"][metric] += value
                
            return {
                "platforms": platform_performance,
                "products": product_performance,
                "total_posts": len(filtered_data)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing performance: {str(e)}")
            return {
                "error": str(e),
                "platforms": {},
                "products": {},
                "total_posts": 0
            }