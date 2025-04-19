"""
Analytics pages for the AdBot application.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import datetime

def analytics_page(data_access, auth_manager, payment_manager):
    """Display analytics and reporting page"""
    try:
        st.title("Analytics")
        
        # Get user and company
        user = auth_manager.get_current_user()
        company = auth_manager.get_current_company()
        
        if not user or not company:
            st.warning("Please log in to view analytics")
            return
        
        # Display debugging info in a cleaner way
        with st.sidebar.expander("🔍 Debug Information", expanded=False):
            st.markdown("#### User & Company")
            st.json({"user": user, "company": company})
        
        # Check if analytics is allowed on current plan
        plan = company.get("plan", "free")
        
        # Get plan details from payment manager
        plan_details = payment_manager.plans.get(plan, {})
        
        # Check if analytics is allowed or requires payment
        has_analytics = False
        
        if plan_details.get("analytics", False) == True:
            # Analytics included in plan
            has_analytics = True
        
        # Display analytics options in a cleaner card
        st.markdown("""
        <div style="background-color:#f0f2f6; padding:15px; border-radius:10px; margin-bottom:15px">
            <h3 style="margin-top:0">Analytics Configuration</h3>
        </div>
        """, unsafe_allow_html=True)
        
        time_periods = ["Last 7 days", "Last 30 days", "Last 90 days"]
        selected_period = st.selectbox("Time Period", time_periods)
        
        # Convert to actual number of days
        days_mapping = {
            "Last 7 days": 7,
            "Last 30 days": 30,
            "Last 90 days": 90
        }
        days = days_mapping.get(selected_period, 30)
        
        # Get analytics data
        try:
            analytics_data = data_access.get_company_analytics(company["id"], days)
            with st.sidebar.expander("Analytics Data", expanded=False):
                st.json(analytics_data)
        except Exception as e:
            st.error(f"Error loading analytics data: {str(e)}")
            analytics_data = {
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
                "engagement_trend": []
            }
        
        # Apply some data manipulations if needed to prevent errors
        if "summary" not in analytics_data:
            analytics_data["summary"] = {
                "total_posts": 0,
                "total_likes": 0,
                "total_shares": 0,
                "total_comments": 0,
                "total_clicks": 0,
                "total_impressions": 0
            }
        
        if "platforms" not in analytics_data:
            analytics_data["platforms"] = {}
            
        if "recent_posts" not in analytics_data:
            analytics_data["recent_posts"] = []
            
        # Display analytics
        if not has_analytics:
            # Option to pay for analytics report
            st.warning("Analytics reports are not included in your current plan.")
            
            # Check if user has sufficient balance
            if payment_manager._check_sufficient_balance(company["id"], "analytics", 1):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown("Unlock detailed analytics and insights to optimize your social media performance.")
                with col2:
                    pay_now = st.button("Pay $0.10 for Analytics Report")
                
                if pay_now:
                    # Record usage
                    payment_manager.record_usage(company["id"], "analytics", 1)
                    has_analytics = True
                    st.success("Payment successful! Showing analytics report...")
                    st.rerun()
            else:
                st.error("Insufficient balance to view analytics. Please add credits.")
                
                if st.button("Go to Billing Page"):
                    st.session_state["current_page"] = "Billing"
                    st.rerun()
        
        # Only show analytics if the plan allows it
        if has_analytics:
            # Display analytics here...
            st.markdown("""
            <div style="background-color:#f0f2f6; padding:15px; border-radius:10px; margin-bottom:15px">
                <h3 style="margin-top:0">Analytics Summary</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Create metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    label="Total Posts", 
                    value=analytics_data["summary"].get("total_posts", 0)
                )
            
            with col2:
                st.metric(
                    label="Total Likes", 
                    value=analytics_data["summary"].get("total_likes", 0)
                )
            
            with col3:
                st.metric(
                    label="Total Shares", 
                    value=analytics_data["summary"].get("total_shares", 0)
                )
            
            with col4:
                st.metric(
                    label="Total Comments", 
                    value=analytics_data["summary"].get("total_comments", 0)
                )
                
            # Get products for the filter
            try:
                products = data_access.get_company_products(company["id"])
                
                # Display platform breakdown
                st.markdown("""
                <div style="background-color:#f0f2f6; padding:15px; border-radius:10px; margin-bottom:15px">
                    <h3 style="margin-top:0">Platform Performance</h3>
                </div>
                """, unsafe_allow_html=True)
                
                # If no platforms data, show a message
                if not analytics_data.get("platforms"):
                    st.info("No platform data available yet. Start posting to see analytics!")
                else:
                    # Display platform stats
                    platform_data = []
                    for platform, stats in analytics_data.get("platforms", {}).items():
                        platform_data.append({
                            "Platform": platform.capitalize(),
                            "Posts": stats.get("post_count", 0),
                            "Likes": stats.get("engagement", {}).get("likes", 0),
                            "Shares": stats.get("engagement", {}).get("shares", 0),
                            "Comments": stats.get("engagement", {}).get("comments", 0)
                        })
                    
                    if platform_data:
                        platform_df = pd.DataFrame(platform_data)
                        st.dataframe(platform_df, use_container_width=True)
                    else:
                        st.info("No platform data available yet.")
                
                # Display recent posts
                st.markdown("""
                <div style="background-color:#f0f2f6; padding:15px; border-radius:10px; margin-bottom:15px">
                    <h3 style="margin-top:0">Recent Posts</h3>
                </div>
                """, unsafe_allow_html=True)
                
                # If no recent posts, show a message
                if not analytics_data.get("recent_posts"):
                    st.info("No recent posts available.")
                else:
                    # Display recent posts
                    for post in analytics_data.get("recent_posts", []):
                        with st.expander(f"{post.get('platform', '').capitalize()} - {post.get('timestamp', '')}"):
                            st.markdown(f"**Content:** {post.get('content', 'No content')}")
                            st.markdown(f"**Likes:** {post.get('likes', 0)} | **Shares:** {post.get('shares', 0)} | **Comments:** {post.get('comments', 0)}")
                            if post.get('url'):
                                st.markdown(f"[View Post]({post.get('url')})")
                
            except Exception as e:
                st.error(f"Error displaying analytics: {str(e)}")
                st.info("No post data available for the selected filters.")
    except Exception as e:
        st.error(f"Error in analytics_page: {str(e)}")
        
        # Show a more user-friendly error message with debugging help
        st.markdown("""
        <div style="background-color:#f8d7da; padding:15px; border-radius:10px; margin-bottom:15px">
            <h3 style="margin-top:0; color:#721c24">We encountered an error</h3>
            <p>Our analytics service is currently experiencing some issues. Please try again later.</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("Technical Details (for support)"):
            st.code(str(e), language="python")
            
        if st.button("Return to Dashboard"):
            st.session_state["current_page"] = "Dashboard"
            st.rerun() 