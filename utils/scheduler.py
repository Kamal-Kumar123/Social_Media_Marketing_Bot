"""
Scheduler module for the AdBot application.
Handles scheduling and automation of ad postings.
"""

import os
import json
import random
import logging
import datetime
import threading
import time
import schedule
from typing import Dict, List, Any, Callable

# Configure logging
logger = logging.getLogger("AdScheduler")

class AdScheduler:
    """Class for scheduling automated ad postings"""
    
    def __init__(self, config, product_manager, content_generator, social_handler, analytics_manager):
        """Initialize the scheduler with required components"""
        self.config = config
        self.product_manager = product_manager
        self.content_generator = content_generator
        self.social_handler = social_handler
        self.analytics_manager = analytics_manager
        self.schedule = schedule
        self.is_running = False
        self.thread = None
        self.schedules = self._load_schedules()
    
    def _load_schedules(self) -> Dict:
        """Load existing schedules from file"""
        schedule_file = "data/schedules.json"
        os.makedirs(os.path.dirname(schedule_file), exist_ok=True)
        
        if os.path.exists(schedule_file):
            try:
                with open(schedule_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading schedules: {str(e)}")
                return {}
        return {}
    
    def _save_schedules(self):
        """Save schedules to file"""
        schedule_file = "data/schedules.json"
        os.makedirs(os.path.dirname(schedule_file), exist_ok=True)
        
        try:
            with open(schedule_file, 'w') as f:
                json.dump(self.schedules, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving schedules: {str(e)}")
    
    def create_post(self, product_id: str, platform: str, format_type: str = "image") -> Dict:
        """Create and post content for a product on a platform"""
        try:
            # Get product data
            product = self.product_manager.get_product(product_id)
            if not product:
                logger.error(f"Product not found: {product_id}")
                return {"success": False, "error": f"Product not found: {product_id}"}
            
            # Generate ad content
            ad_content = self.content_generator.create_ad_content(product, platform, format_type)
            
            # Post to platform
            post_result = self.social_handler.post_ad(ad_content)
            
            # Collect metrics if the post was successful
            if post_result["success"]:
                self.analytics_manager.collect_metrics(post_result)
            
            return post_result
        except Exception as e:
            logger.error(f"Error creating post: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def schedule_post(self, product_id: str, platform: str, schedule_time: str, 
                      format_type: str = "image", recurrence: str = None) -> str:
        """Schedule a post for a specific time"""
        try:
            # Validate product and platform
            product = self.product_manager.get_product(product_id)
            if not product:
                return f"Product not found: {product_id}"
            
            if platform not in self.config.platforms:
                return f"Platform not configured: {platform}"
            
            # Generate a schedule ID
            schedule_id = f"SCH_{len(self.schedules) + 1}_{int(time.time())}"
            
            # Parse schedule time
            if schedule_time == "now":
                # Post immediately
                post_result = self.create_post(product_id, platform, format_type)
                if post_result["success"]:
                    return f"Posted successfully, post_id: {post_result['post_id']}"
                else:
                    return f"Failed to post: {post_result.get('error', 'Unknown error')}"
            
            # Create schedule entry
            schedule_entry = {
                "id": schedule_id,
                "product_id": product_id,
                "platform": platform,
                "format_type": format_type,
                "schedule_time": schedule_time,
                "recurrence": recurrence,
                "created_at": datetime.datetime.now().isoformat(),
                "status": "scheduled"
            }
            
            # Add to schedules
            self.schedules[schedule_id] = schedule_entry
            self._save_schedules()
            
            # Add to schedule
            self._add_to_schedule(schedule_entry)
            
            return schedule_id
        except Exception as e:
            logger.error(f"Error scheduling post: {str(e)}")
            return f"Error: {str(e)}"
    
    def _add_to_schedule(self, schedule_entry: Dict):
        """Add a schedule entry to the scheduler"""
        schedule_time = schedule_entry["schedule_time"]
        schedule_id = schedule_entry["id"]
        product_id = schedule_entry["product_id"]
        platform = schedule_entry["platform"]
        format_type = schedule_entry["format_type"]
        recurrence = schedule_entry["recurrence"]
        
        # Create the job function
        def job():
            try:
                logger.info(f"Running scheduled post: {schedule_id}")
                post_result = self.create_post(product_id, platform, format_type)
                
                if post_result["success"]:
                    logger.info(f"Scheduled post successful: {schedule_id}, post_id: {post_result['post_id']}")
                    self.schedules[schedule_id]["last_run"] = datetime.datetime.now().isoformat()
                    self.schedules[schedule_id]["last_post_id"] = post_result["post_id"]
                    self.schedules[schedule_id]["status"] = "completed"
                else:
                    logger.error(f"Scheduled post failed: {schedule_id}, error: {post_result.get('error', 'Unknown error')}")
                    self.schedules[schedule_id]["last_error"] = post_result.get("error", "Unknown error")
                    self.schedules[schedule_id]["status"] = "failed"
                
                self._save_schedules()
            except Exception as e:
                logger.error(f"Error running scheduled post: {str(e)}")
                self.schedules[schedule_id]["last_error"] = str(e)
                self.schedules[schedule_id]["status"] = "failed"
                self._save_schedules()
        
        # Schedule based on time specification
        if schedule_time == "daily":
            # Random time during the day
            hour = random.randint(9, 17)  # 9 AM to 5 PM
            minute = random.randint(0, 59)
            self.schedule.every().day.at(f"{hour:02d}:{minute:02d}").do(job)
            logger.info(f"Scheduled daily post at {hour:02d}:{minute:02d}: {schedule_id}")
        elif schedule_time.startswith("at:"):
            # Schedule for a specific time (format: "at:HH:MM")
            time_str = schedule_time[3:]
            self.schedule.every().day.at(time_str).do(job)
            logger.info(f"Scheduled post at {time_str}: {schedule_id}")
        elif schedule_time.startswith("date:"):
            # Schedule for a specific date and time (format: "date:YYYY-MM-DD HH:MM")
            date_time_str = schedule_time[5:]
            target_dt = datetime.datetime.strptime(date_time_str, "%Y-%m-%d %H:%M")
            
            # Calculate seconds until the target time
            now = datetime.datetime.now()
            seconds_until = (target_dt - now).total_seconds()
            
            if seconds_until <= 0:
                logger.warning(f"Scheduled time is in the past: {schedule_id}")
                return
            
            # Schedule for the specific date and time
            self.schedule.every(seconds_until).seconds.do(job)
            logger.info(f"Scheduled post for {date_time_str}: {schedule_id}")
        
        # Handle recurrence
        if recurrence and recurrence != "once":
            if recurrence == "daily":
                self.schedule.every().day.at(schedule_time.split(":")[1]).do(job)
            elif recurrence == "weekly":
                self.schedule.every().week.at(schedule_time.split(":")[1]).do(job)
            elif recurrence == "monthly":
                # This is a bit tricky with schedule library, we'd need a more complex approach
                pass
    
    def cancel_schedule(self, schedule_id: str) -> bool:
        """Cancel a scheduled post"""
        try:
            if schedule_id not in self.schedules:
                logger.error(f"Schedule not found: {schedule_id}")
                return False
            
            # Update status
            self.schedules[schedule_id]["status"] = "cancelled"
            self._save_schedules()
            
            # Note: With the schedule library, we can't easily cancel a specific job
            # This is a limitation. In a real implementation, we'd need a more robust approach.
            
            logger.info(f"Cancelled schedule: {schedule_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling schedule: {str(e)}")
            return False
    
    def get_all_schedules(self) -> Dict:
        """Get all scheduled posts"""
        return self.schedules
    
    def get_schedule(self, schedule_id: str) -> Dict:
        """Get a specific schedule"""
        return self.schedules.get(schedule_id)
    
    def start(self):
        """Start the scheduler thread"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return False
        
        def run_scheduler():
            self.is_running = True
            logger.info("Scheduler started")
            
            while self.is_running:
                self.schedule.run_pending()
                time.sleep(1)
            
            logger.info("Scheduler stopped")
        
        self.thread = threading.Thread(target=run_scheduler)
        self.thread.daemon = True
        self.thread.start()
        
        return True
    
    def stop(self):
        """Stop the scheduler thread"""
        if not self.is_running:
            logger.warning("Scheduler is not running")
            return False
        
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        
        logger.info("Scheduler stopped")
        return True
    
    def auto_schedule_for_product(self, product_id: str, 
                                 platforms: List[str] = None, 
                                 days: int = 7,
                                 posts_per_day: int = 2) -> List[str]:
        """Automatically create a schedule for a product across platforms"""
        try:
            product = self.product_manager.get_product(product_id)
            if not product:
                return {"error": f"Product not found: {product_id}"}
            
            if platforms is None:
                platforms = self.config.platforms
            
            # Validate platforms
            valid_platforms = [p for p in platforms if p in self.config.platforms]
            if not valid_platforms:
                return {"error": "No valid platforms specified"}
            
            schedule_ids = []
            
            # Create schedules for the next 'days' days
            for day in range(days):
                day_date = datetime.datetime.now() + datetime.timedelta(days=day)
                
                # Schedule 'posts_per_day' posts per day, distributed across platforms
                for post_num in range(posts_per_day):
                    # Pick a random platform from the valid ones
                    platform = random.choice(valid_platforms)
                    
                    # Generate a random time (9 AM to 7 PM)
                    hour = random.randint(9, 19)
                    minute = random.randint(0, 59)
                    
                    schedule_time = f"date:{day_date.strftime('%Y-%m-%d')} {hour:02d}:{minute:02d}"
                    
                    # Schedule the post
                    schedule_id = self.schedule_post(
                        product_id=product_id,
                        platform=platform,
                        schedule_time=schedule_time,
                        format_type="image",
                        recurrence="once"
                    )
                    
                    if not schedule_id.startswith("Error") and not schedule_id.startswith("Product not found"):
                        schedule_ids.append(schedule_id)
            
            return schedule_ids
        except Exception as e:
            logger.error(f"Error auto-scheduling for product: {str(e)}")
            return {"error": str(e)} 