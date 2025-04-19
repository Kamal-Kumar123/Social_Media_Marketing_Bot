"""
Analytics Manager module for the AdBot application.
Handles collection, analysis, and reporting of social media marketing performance.
"""

import os
import json
import logging
import datetime
from typing import Dict, List, Any, Optional, Union

# Configure logging
logger = logging.getLogger("AnalyticsManager")

class AnalyticsManager:
    """Class for tracking and analyzing social media campaign performance"""
    
    def __init__(self, config, social_handler):
        """Initialize the analytics manager with the provided config and social media handler"""
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
    
    def get_best_performing_platform(self, product_id: str = None, days: int = 30) -> Dict:
        """Determine the best performing platform for a product or overall"""
        performance = self.analyze_performance(product_id=product_id, days=days)
        
        if "error" in performance:
            return {"error": performance["error"]}
        
        platform_scores = {}
        
        # Calculate a score for each platform
        for platform, data in performance["platforms"].items():
            engagement = data["engagement"]
            post_count = data["post_count"]
            
            if post_count == 0:
                continue
            
            # Calculate average engagement metrics
            avg_engagement = {}
            for metric, value in engagement.items():
                avg_engagement[metric] = value / post_count
            
            # Calculate a simple score (can be customized based on business goals)
            score = 0
            if "impressions" in avg_engagement:
                score += avg_engagement["impressions"] * 0.3
            if "likes" in avg_engagement:
                score += avg_engagement["likes"] * 0.2
            if "comments" in avg_engagement:
                score += avg_engagement["comments"] * 0.3
            if "clicks" in avg_engagement:
                score += avg_engagement["clicks"] * 0.4
            if "shares" in avg_engagement or "retweets" in avg_engagement:
                shares = avg_engagement.get("shares", 0) + avg_engagement.get("retweets", 0)
                score += shares * 0.5
            
            platform_scores[platform] = {
                "score": score,
                "post_count": post_count,
                "avg_engagement": avg_engagement
            }
        
        # Find the best platform
        best_platform = None
        best_score = -1
        
        for platform, data in platform_scores.items():
            if data["score"] > best_score:
                best_score = data["score"]
                best_platform = platform
        
        return {
            "best_platform": best_platform,
            "platform_scores": platform_scores
        }
    
    def get_engagement_over_time(self, product_id: str = None, platform: str = None, days: int = 30) -> Dict:
        """Get engagement metrics over time for trending analysis"""
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
            
            # Sort data by timestamp
            filtered_data.sort(key=lambda x: x["timestamp"])
            
            # Group metrics by date
            daily_metrics = {}
            
            for metrics in filtered_data:
                date_str = metrics["timestamp"].split("T")[0]  # Get just the date part
                
                if date_str not in daily_metrics:
                    daily_metrics[date_str] = {
                        "post_count": 0,
                        "engagement": {}
                    }
                
                daily_metrics[date_str]["post_count"] += 1
                
                # Aggregate engagement metrics
                for metric, value in metrics.get("engagement", {}).items():
                    if metric not in daily_metrics[date_str]["engagement"]:
                        daily_metrics[date_str]["engagement"][metric] = 0
                    daily_metrics[date_str]["engagement"][metric] += value
            
            # Convert to lists for visualization
            dates = list(daily_metrics.keys())
            engagement_data = {}
            
            # Initialize with empty lists for each metric
            all_metrics = set()
            for date_data in daily_metrics.values():
                all_metrics.update(date_data["engagement"].keys())
            
            for metric in all_metrics:
                engagement_data[metric] = []
            
            # Populate with values
            for date in dates:
                for metric in all_metrics:
                    value = daily_metrics[date]["engagement"].get(metric, 0)
                    engagement_data[metric].append(value)
            
            return {
                "dates": dates,
                "engagement_data": engagement_data,
                "daily_metrics": daily_metrics
            }
            
        except Exception as e:
            logger.error(f"Error getting engagement over time: {str(e)}")
            return {
                "error": str(e),
                "dates": [],
                "engagement_data": {}
            } 