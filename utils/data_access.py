"""
Data Access module for the AdBot application.
Ensures data isolation in the multi-tenant system.
"""

import os
import json
import logging
import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# Configure logging
logger = logging.getLogger("DataAccess")

class DataAccessManager:
    """Class for handling data access with multi-tenant isolation"""
    
    def __init__(self):
        """Initialize the data access manager"""
        # Ensure Firebase is initialized before accessing Firestore
        try:
            # Check if Firebase app exists already
            if not firebase_admin._apps:
                firebase_cred_path = os.getenv("FIREBASE_CRED_PATH", "firebase-credentials.json")
                cred = credentials.Certificate(firebase_cred_path)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase initialized successfully in DataAccessManager")
            
            # Only get the Firestore client after Firebase is initialized
            self.db = firestore.client()
        except Exception as e:
            logger.error(f"Error initializing Firebase/Firestore: {str(e)}")
            raise  # Re-raise to prevent silently continuing with an uninitialized Firebase
    
    def get_product(self, product_id, company_id):
        """Get a product by ID for a specific company"""
        try:
            product_ref = self.db.collection("products").document(product_id).get()
            
            if not product_ref.exists:
                return None
            
            product = product_ref.to_dict()
            
            # Verify the product belongs to the company
            if product.get("company_id") != company_id:
                logger.warning(f"Attempted access to product {product_id} by unauthorized company {company_id}")
                return None
            
            return {
                "id": product_id,
                **product
            }
        except Exception as e:
            logger.error(f"Error getting product: {str(e)}")
            return None
    
    def get_company_products(self, company_id):
        """Get all products for a company"""
        try:
            products_ref = self.db.collection("products").where("company_id", "==", company_id).get()
            
            products = {}
            for product in products_ref:
                product_data = product.to_dict()
                products[product.id] = {
                    "id": product.id,
                    **product_data
                }
            
            return products
        except Exception as e:
            logger.error(f"Error getting company products: {str(e)}")
            return {}
    
    def add_product(self, product_data, company_id):
        """Add a new product for a company"""
        try:
            # Ensure company_id is set
            product_data["company_id"] = company_id
            product_data["created_at"] = datetime.datetime.now().isoformat()
            
            # Add product
            product_ref = self.db.collection("products").add(product_data)
            product_id = product_ref[1].id
            
            return product_id
        except Exception as e:
            logger.error(f"Error adding product: {str(e)}")
            return None
    
    def update_product(self, product_id, product_data, company_id):
        """Update a product for a company"""
        try:
            # Verify the product belongs to the company
            product_ref = self.db.collection("products").document(product_id).get()
            
            if not product_ref.exists:
                return False
            
            product = product_ref.to_dict()
            
            if product.get("company_id") != company_id:
                logger.warning(f"Attempted update to product {product_id} by unauthorized company {company_id}")
                return False
            
            # Ensure company_id can't be changed
            product_data["company_id"] = company_id
            product_data["updated_at"] = datetime.datetime.now().isoformat()
            
            # Update product
            self.db.collection("products").document(product_id).update(product_data)
            
            return True
        except Exception as e:
            logger.error(f"Error updating product: {str(e)}")
            return False
    
    def delete_product(self, product_id, company_id):
        """Delete a product for a company"""
        try:
            # Verify the product belongs to the company
            product_ref = self.db.collection("products").document(product_id).get()
            
            if not product_ref.exists:
                return False
            
            product = product_ref.to_dict()
            
            if product.get("company_id") != company_id:
                logger.warning(f"Attempted deletion of product {product_id} by unauthorized company {company_id}")
                return False
            
            # Delete product
            self.db.collection("products").document(product_id).delete()
            
            return True
        except Exception as e:
            logger.error(f"Error deleting product: {str(e)}")
            return False
    
    def get_company_analytics(self, company_id, days=30):
        """Get analytics data for a company"""
        try:
            # Calculate start date
            start_date = datetime.datetime.now() - datetime.timedelta(days=days)
            start_date_str = start_date.isoformat()
            
            # Modified approach to avoid requiring composite index
            # First get all posts for the company
            posts_ref = self.db.collection("posts").where("company_id", "==", company_id).get()
            
            # Then filter by timestamp in Python instead of in the query
            posts = []
            for post in posts_ref:
                post_data = post.to_dict()
                post_data["id"] = post.id
                if "timestamp" in post_data and post_data["timestamp"] >= start_date_str:
                    posts.append(post_data)
            
            # If no posts, return empty data
            if not posts:
                return {
                    "summary": {
                        "total_posts": 0,
                        "total_likes": 0,
                        "total_shares": 0,
                        "total_comments": 0,
                        "total_clicks": 0,
                        "total_impressions": 0
                    },
                    "platforms": {},
                    "recent_posts": [],
                    "engagement_trend": [],
                    "platform_stats": {}
                }
            
            # Get analytics for each post
            analytics_data = []
            for post in posts:
                post_analytics = self.db.collection("analytics").where("post_id", "==", post["id"]).get()
                for analytics in post_analytics:
                    analytics_data.append(analytics.to_dict())
            
            # Process analytics data
            return self._process_analytics(posts, analytics_data)
        
        except Exception as e:
            logger.error(f"Error getting company analytics: {str(e)}")
            # Return empty data
            return {
                "summary": {
                    "total_posts": 0,
                    "total_likes": 0,
                    "total_shares": 0,
                    "total_comments": 0,
                    "total_clicks": 0,
                    "total_impressions": 0
                },
                "platforms": {},
                "recent_posts": [],
                "engagement_trend": [],
                "platform_stats": {}
            }
    
    def _process_analytics(self, posts, analytics_data):
        """Process analytics data into a structured format"""
        result = {
            "summary": {
                "total_posts": len(posts),
                "total_likes": 0,
                "total_shares": 0, 
                "total_comments": 0,
                "total_clicks": 0,
                "total_impressions": 0
            },
            "platforms": {},
            "recent_posts": [],
            "engagement_trend": [],
            "platform_stats": {}
        }
        
        try:
            # Create a dictionary of analytics by post_id for easier lookup
            analytics_by_post_id = {}
            for item in analytics_data:
                post_id = item.get("post_id")
                if post_id:
                    analytics_by_post_id[post_id] = item
            
            for post in posts:
                post_id = post.get("id")
                platform = post.get("platform")
                
                # Get analytics for this post
                post_analytics = analytics_by_post_id.get(post_id, {})
                
                # Add engagement metrics to summary
                likes = post_analytics.get("likes", 0)
                shares = post_analytics.get("shares", 0)
                comments = post_analytics.get("comments", 0)
                clicks = post_analytics.get("clicks", 0)
                impressions = post_analytics.get("impressions", 0)
                
                result["summary"]["total_likes"] += likes
                result["summary"]["total_shares"] += shares
                result["summary"]["total_comments"] += comments
                result["summary"]["total_clicks"] += clicks
                result["summary"]["total_impressions"] += impressions
                
                # Add to recent posts
                result["recent_posts"].append({
                    "id": post_id,
                    "platform": platform,
                    "content": post.get("content", ""),
                    "timestamp": post.get("timestamp", ""),
                    "likes": likes,
                    "shares": shares,
                    "comments": comments,
                    "url": post.get("url", "")
                })
                
                # Update platform stats
                if platform not in result["platforms"]:
                    result["platforms"][platform] = {
                        "post_count": 0,
                        "engagement": {
                            "likes": 0,
                            "shares": 0,
                            "comments": 0,
                            "clicks": 0,
                            "impressions": 0
                        },
                        "posts": []
                    }
                
                result["platforms"][platform]["post_count"] += 1
                result["platforms"][platform]["posts"].append(post_id)
                result["platforms"][platform]["engagement"]["likes"] += likes
                result["platforms"][platform]["engagement"]["shares"] += shares
                result["platforms"][platform]["engagement"]["comments"] += comments
                result["platforms"][platform]["engagement"]["clicks"] += clicks
                result["platforms"][platform]["engagement"]["impressions"] += impressions
                
            # Sort recent posts by timestamp
            result["recent_posts"] = sorted(
                result["recent_posts"], 
                key=lambda x: x.get("timestamp", ""), 
                reverse=True
            )[:5]  # Get 5 most recent posts
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing analytics: {str(e)}")
            return result
    
    def log_event(self, event_type, data, company_id, user_id=None):
        """Log an event with company and user context"""
        try:
            event = {
                "type": event_type,
                "data": data,
                "company_id": company_id,
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            if user_id:
                event["user_id"] = user_id
            
            # Log to database
            self.db.collection("events").add(event)
            
            return True
        except Exception as e:
            logger.error(f"Error logging event: {str(e)}")
            return False
    
    def record_post(self, post_data, company_id):
        """Record a post with company context"""
        try:
            # Ensure company_id is set
            post_data["company_id"] = company_id
            post_data["timestamp"] = datetime.datetime.now().isoformat()
            
            # Add post
            post_ref = self.db.collection("posts").add(post_data)
            post_id = post_ref[1].id
            
            return post_id
        except Exception as e:
            logger.error(f"Error recording post: {str(e)}")
            return None
    
    def record_post_analytics(self, post_id, analytics_data, company_id):
        """Record analytics for a post"""
        try:
            # Verify the post belongs to the company
            post_ref = self.db.collection("posts").document(post_id).get()
            
            if not post_ref.exists:
                return False
            
            post = post_ref.to_dict()
            
            if post.get("company_id") != company_id:
                logger.warning(f"Attempted to record analytics for post {post_id} by unauthorized company {company_id}")
                return False
            
            # Ensure company_id and post_id are set
            analytics_data["company_id"] = company_id
            analytics_data["post_id"] = post_id
            analytics_data["timestamp"] = datetime.datetime.now().isoformat()
            
            # Add analytics
            analytics_ref = self.db.collection("post_analytics").add(analytics_data)
            analytics_id = analytics_ref[1].id
            
            return analytics_id
        except Exception as e:
            logger.error(f"Error recording post analytics: {str(e)}")
            return None
    
    def get_company_schedules(self, company_id):
        """Get all scheduled posts for a company"""
        try:
            schedules_ref = self.db.collection("schedules").where("company_id", "==", company_id).get()
            
            schedules = {}
            for schedule in schedules_ref:
                schedule_data = schedule.to_dict()
                schedules[schedule.id] = {
                    "id": schedule.id,
                    **schedule_data
                }
            
            return schedules
        except Exception as e:
            logger.error(f"Error getting company schedules: {str(e)}")
            return {}
    
    def add_schedule(self, schedule_data, company_id):
        """Add a new schedule for a company"""
        try:
            # Ensure company_id is set
            schedule_data["company_id"] = company_id
            schedule_data["created_at"] = datetime.datetime.now().isoformat()
            
            # Add schedule
            schedule_ref = self.db.collection("schedules").add(schedule_data)
            schedule_id = schedule_ref[1].id
            
            return schedule_id
        except Exception as e:
            logger.error(f"Error adding schedule: {str(e)}")
            return None
    
    def update_schedule(self, schedule_id, schedule_data, company_id):
        """Update a schedule for a company"""
        try:
            # Verify the schedule belongs to the company
            schedule_ref = self.db.collection("schedules").document(schedule_id).get()
            
            if not schedule_ref.exists:
                return False
            
            schedule = schedule_ref.to_dict()
            
            if schedule.get("company_id") != company_id:
                logger.warning(f"Attempted update to schedule {schedule_id} by unauthorized company {company_id}")
                return False
            
            # Ensure company_id can't be changed
            schedule_data["company_id"] = company_id
            schedule_data["updated_at"] = datetime.datetime.now().isoformat()
            
            # Update schedule
            self.db.collection("schedules").document(schedule_id).update(schedule_data)
            
            return True
        except Exception as e:
            logger.error(f"Error updating schedule: {str(e)}")
            return False 