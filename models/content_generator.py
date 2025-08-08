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
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, List, Any, Optional, Union

# Configure logging
logger = logging.getLogger("ContentGenerator")

class ContentGenerator:
    """Class for generating ad content using AI"""
    
    def __init__(self, config):
        """Initialize the content generator with the provided config"""
        self.config = config
        # Set the API key in the openai module for compatibility with older code
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
            
            # Create client with explicit API key
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
            
            # Create client with explicit API key
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
            
            # Multiple fallback approaches for different API key formats
            
            # Get any project ID from environment
            project_id = os.environ.get("OPENAI_PROJECT_ID")
            
            # Initialize the client with the new OpenAI SDK format (v1.x)
            from openai import OpenAI
            
            # Log key type for debugging
            key_type = 'project-scoped' if api_key.startswith('sk-proj-') else 'standard'
            logger.info(f"Using API key type: {key_type}")
            
            # We'll try multiple approaches in sequence, with fallbacks if errors occur
            image_content = None
            
            # First attempt: Try using the OpenAI client with project_id if available
            try:
                logger.info("Attempt 1: Using OpenAI client with explicit parameters")
                client_args = {"api_key": api_key}
                if project_id and api_key.startswith('sk-proj-'):
                    client_args["project"] = project_id
                    logger.info(f"Using project ID: {project_id}")
                
                client = OpenAI(**client_args)
                
                # Try DALL-E 2 first as it might have fewer restrictions
                response = client.images.generate(
                    model="dall-e-2",
                    prompt=prompt,
                    n=1,
                    size=size
                )
                
                # Extract image URL from the response
                image_url = response.data[0].url
                logger.info(f"Image generated successfully (Method 1), URL: {image_url[:30]}...")
                
                # Download the image
                image_response = requests.get(image_url)
                
                if image_response.status_code == 200:
                    logger.info("Successfully downloaded generated image")
                    image_content = image_response.content
                else:
                    logger.error(f"Failed to download generated image: {image_response.status_code}")
                    raise Exception(f"Download failed with status: {image_response.status_code}")
            except Exception as e1:
                logger.error(f"Attempt 1 failed: {str(e1)}")
                
                # Second attempt: Use a placeholder image from a free API
                try:
                    logger.info("Attempt 2: Using placeholder image from external API")
                    # Use Unsplash API with a search term based on the prompt
                    search_term = prompt.split()[0] if len(prompt.split()) > 0 else "product"
                    placeholder_url = f"https://source.unsplash.com/1024x1024/?{search_term}"
                    
                    image_response = requests.get(placeholder_url)
                    if image_response.status_code == 200:
                        logger.info(f"Successfully retrieved placeholder image from {placeholder_url}")
                        image_content = image_response.content
                    else:
                        logger.error(f"Failed to get placeholder image: {image_response.status_code}")
                        raise Exception(f"Placeholder image request failed with status: {image_response.status_code}")
                except Exception as e2:
                    logger.error(f"Attempt 2 failed: {str(e2)}")
                    
                    # Third attempt: Generate a locally-created placeholder image
                    image_content = self.generate_placeholder_image(prompt)
            
            return image_content
                
        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            # Print the full error details to help with debugging
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Detailed error: {error_details}")
            
            # Final fallback - generate a local image
            return self.generate_placeholder_image(prompt)
    
    def generate_placeholder_image(self, prompt_text: str) -> bytes:
        """Generate a simple placeholder image when API-based generation fails"""
        try:
            logger.info("Generating local placeholder image")
            from PIL import Image, ImageDraw
            import io
            
            # Create a blank image with a solid color
            width, height = 800, 600
            img = Image.new('RGB', (width, height), color=(73, 109, 137))
            draw = ImageDraw.Draw(img)
            
            # Draw some rectangles to create a simple design
            draw.rectangle([(100, 100), (width-100, height-100)], fill=(50, 80, 100))
            draw.rectangle([(150, 150), (width-150, height-150)], fill=(60, 90, 120))
            draw.rectangle([(250, 250), (width-250, height-250)], fill=(80, 120, 160))
            
            # Draw a diagonal pattern
            for i in range(0, width, 20):
                draw.line([(i, 0), (i+100, height)], fill=(200, 200, 240), width=1)
            
            # Save to bytes
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            image_bytes = img_byte_arr.getvalue()
            logger.info("Successfully generated local placeholder image")
            return image_bytes
            
        except Exception as e:
            logger.error(f"Error generating placeholder image: {str(e)}")
            # This should never fail, but if it does, return an empty byte array
            return bytes()
    
    def add_text_to_image(self, image_path: str, text: Dict) -> str:
        """Add text overlay to an image
        
        Args:
            image_path: Path to the image file
            text: Dictionary containing text to overlay (headline, tagline, etc)
            
        Returns:
            Path to the new image with text overlay
        """
        try:
            # Open the image
            img = Image.open(image_path)
            
            # Create a drawing context
            draw = ImageDraw.Draw(img)
            
            # Try to find a font - use default if necessary
            try:
                # Try to use a common system font
                headline_font = ImageFont.truetype("Arial", 48)
                tagline_font = ImageFont.truetype("Arial", 36)
            except IOError:
                # Fall back to default font
                headline_font = ImageFont.load_default()
                tagline_font = headline_font
            
            # Get image dimensions
            width, height = img.size
            
            # Add headline at the top
            if "headline" in text and text["headline"]:
                headline = text["headline"]
                # Position at the top with padding
                draw.text((width/2, height*0.1), headline, fill="white", font=headline_font, 
                         anchor="mt", stroke_width=2, stroke_fill="black")
            
            # Add tagline or call to action at the bottom
            if "tagline" in text and text["tagline"]:
                tagline = text["tagline"]
                # Position at the bottom with padding
                draw.text((width/2, height*0.9), tagline, fill="white", font=tagline_font,
                         anchor="mb", stroke_width=2, stroke_fill="black")
                
            # Add brand name or logo if provided
            if "brand" in text and text["brand"]:
                brand = text["brand"]
                # Position in the bottom right corner
                draw.text((width*0.95, height*0.95), brand, fill="white", font=tagline_font,
                         anchor="rb", stroke_width=2, stroke_fill="black")
            
            # Save the modified image
            new_image_path = image_path.replace(".png", "_with_text.png")
            img.save(new_image_path)
            
            logger.info(f"Successfully added text overlay to image: {new_image_path}")
            return new_image_path
            
        except Exception as e:
            logger.error(f"Error adding text to image: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return image_path  # Return original path if there was an error
    
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
        
        ad_copy = self.generate_ad_copy(product, platform, tone, length)
        ad_content["copy"] = ad_copy
        
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
                
                # Extract headline and tagline from ad copy
                lines = ad_copy.strip().split('\n')
                text_overlay = {}
                
                if len(lines) > 0:
                    text_overlay["headline"] = lines[0]  # First line as headline
                
                # Look for a call-to-action in the ad copy
                for line in lines:
                    if "call" in line.lower() or "click" in line.lower() or "visit" in line.lower() or "buy" in line.lower():
                        text_overlay["tagline"] = line
                        break
                else:
                    # If no call-to-action found, use the last line as tagline
                    if len(lines) > 1:
                        text_overlay["tagline"] = lines[-1]
                
                # Add brand/product name
                text_overlay["brand"] = product["name"]
                
                # Add text overlay to the image
                image_with_text = self.add_text_to_image(image_path, text_overlay)
                ad_content["image_path"] = image_with_text
        
        # Add hashtags for appropriate platforms
        if platform in ["instagram", "twitter", "tiktok"]:
            ad_content["hashtags"] = self.generate_hashtags(product, platform)
        
        return ad_content
    
    def generate_hashtags(self, product: Dict, platform: str) -> List[str]:
        """Generate relevant hashtags for the product and platform"""
        try:
            # Initialize the client with the new OpenAI SDK format (v1.x)
            from openai import OpenAI
            
            # Create client with explicit API key 
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