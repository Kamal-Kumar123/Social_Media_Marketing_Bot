"""
Content Generator module for the AdBot application.
Handles creation of ad copy, images, and hashtags using AI tools.
"""

import os
import time
import logging
import datetime
import requests
import openai
import io
from PIL import Image
from typing import Dict, List, Any, Optional, Union

# Configure logging
logger = logging.getLogger("ContentGenerator")

class ContentGenerator:
    """Class for generating ad content using AI"""
    
    def __init__(self, config):
        """Initialize the content generator with the provided config"""
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
            
            # Initialize the client with the new OpenAI SDK format (v1.x)
            from openai import OpenAI
            client = OpenAI(api_key=self.config.openai_api_key)
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert marketing copywriter specializing in social media ads."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            # Updated format for new API response
            ad_copy = response.choices[0].message.content.strip()
            logger.info(f"Generated ad copy for {product['name']} on {platform}")
            
            return ad_copy
            
        except Exception as e:
            logger.error(f"Error generating ad copy: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Check out our amazing {product['name']}! {' '.join(product['features'][:2])}. Learn more now!"
    
    def generate_image_prompt(self, product: Dict, platform: str, style: str) -> str:
        """Generate a prompt for image creation based on product details"""
        try:
            # Initialize the client with the new OpenAI SDK format (v1.x)
            from openai import OpenAI
            client = OpenAI(api_key=self.config.openai_api_key)
            
            response = client.chat.completions.create(
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
            
            # Updated format for new API response
            image_prompt = response.choices[0].message.content.strip()
            logger.info(f"Generated image prompt for {product['name']}")
            
            return image_prompt
            
        except Exception as e:
            logger.error(f"Error generating image prompt: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Professional photo of {product['name']} in {style} style, appealing to {product['target_audience']}"
    
    def generate_image(self, prompt: str, size: str = "1024x1024") -> bytes:
        """Generate an image using DALL-E based on the prompt"""
        try:
            # Log API key check (don't log the full key for security)
            api_key = self.config.openai_api_key
            if not api_key:
                logger.error("OpenAI API key is missing")
                return None
            
            logger.info(f"Attempting to generate image with prompt: {prompt[:30]}...")
            
            # Initialize the client with the new OpenAI SDK format (v1.x)
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            # Generate image using the new API format
            response = client.images.generate(
                model="dall-e-3",  # Use DALL-E 3 for better quality
                prompt=prompt,
                n=1,
                size=size
            )
            
            # Extract image URL from the response
            image_url = response.data[0].url
            logger.info(f"Image generated successfully, URL: {image_url[:30]}...")
            
            # Download the image
            image_response = requests.get(image_url)
            
            if image_response.status_code == 200:
                logger.info("Successfully downloaded generated image")
                return image_response.content
            else:
                logger.error(f"Failed to download generated image: {image_response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            # Print the full error details to help with debugging
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Detailed error: {error_details}")
            
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
                image_path = f"data/images/{product['id']}_{platform}_{timestamp}.png"
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
            # Initialize the client with the new OpenAI SDK format (v1.x)
            from openai import OpenAI
            client = OpenAI(api_key=self.config.openai_api_key)
            
            response = client.chat.completions.create(
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
            
            # Updated format for new API response
            hashtags = [tag.strip() for tag in response.choices[0].message.content.split(',')]
            hashtags = [tag if tag.startswith('#') else f"#{tag}" for tag in hashtags]
            
            return hashtags
            
        except Exception as e:
            logger.error(f"Error generating hashtags: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return [f"#{product['name'].replace(' ', '')}", "#newproduct", "#musthave"] 