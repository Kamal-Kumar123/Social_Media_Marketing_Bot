"""
Analytics pages for the AdBot application.
"""

import streamlit as st
import pandas as pd
import datetime
import altair as alt

def analytics_page(data_access, auth_manager, payment_manager):
    """Display analytics and reporting page"""
    try:
        # Simple title like the schedule page
        st.title("Analytics")
        
        # Get user and company
        user = auth_manager.get_current_user()
        company = auth_manager.get_current_company()
        
        if not user or not company:
            st.warning("Please log in to view analytics")
            return
        
        # Check if analytics is allowed on current plan
        plan = company.get("plan", "free")
        
        # Get plan details from payment manager
        plan_details = payment_manager.plans.get(plan, {})
        
        # Check if analytics is allowed or requires payment
        has_analytics = False
        
        if plan_details.get("analytics", False) == True:
            # Analytics included in plan
            has_analytics = True
        
        # Simple time range selection
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
            # Use the same warning style as in the schedule page
            st.warning("Analytics reports are not included in your current plan. Please upgrade to unlock this feature.")
            
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
            return
        
        # Only show analytics if the plan allows it
        if has_analytics:
            # Simple summary section
            st.subheader("Performance Summary")
            
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
            
            # Add a separator
            st.markdown("---")
                
            # Get products for the filter
            try:
                products = data_access.get_company_products(company["id"])
                
                # Platform breakdown section
                st.subheader("Platform Performance")
                
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
                        
                        # Create a visualization with Altair (simpler styling)
                        if len(platform_data) > 0:
                            df_long = pd.melt(
                                platform_df, 
                                id_vars=['Platform'], 
                                value_vars=['Likes', 'Shares', 'Comments'],
                                var_name='Metric', 
                                value_name='Count'
                            )
                            
                            chart = alt.Chart(df_long).mark_bar().encode(
                                x=alt.X('Platform:N', title=None),
                                y=alt.Y('Count:Q', title='Engagement Count'),
                                color=alt.Color('Metric:N'),
                                tooltip=['Platform', 'Metric', 'Count']
                            ).properties(
                                height=300
                            )
                            
                            st.altair_chart(chart, use_container_width=True)
                        
                        # Show the raw data in a table
                        st.dataframe(platform_df, use_container_width=True, hide_index=True)
                    else:
                        st.info("No platform data available yet.")
                
                # Add a separator
                st.markdown("---")
                
                # Recent posts section
                st.subheader("Recent Posts")
                
                # If no recent posts, show a message
                if not analytics_data.get("recent_posts"):
                    st.info("No recent posts available.")
                else:
                    # Display recent posts with simpler styling
                    for post in analytics_data.get("recent_posts", []):
                        platform = post.get('platform', '').capitalize()
                        date = post.get('timestamp', '')
                        
                        st.markdown(f"""
                        <div style="border: 1px solid #eee; padding: 15px; margin-bottom: 10px; border-radius: 5px;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                                <span style="font-weight: bold;">{platform}</span>
                                <span style="font-size: 12px; color: #777;">{date}</span>
                            </div>
                            <p style="margin-bottom: 10px;">{post.get('content', 'No content')}</p>
                            <div>
                                <span style="margin-right: 15px;">❤️ {post.get('likes', 0)} Likes</span>
                                <span style="margin-right: 15px;">🔄 {post.get('shares', 0)} Shares</span>
                                <span style="margin-right: 15px;">💬 {post.get('comments', 0)} Comments</span>
                            </div>
                            {f'<a href="{post.get("url")}" target="_blank" style="display: inline-block; margin-top: 10px;">View Post →</a>' if post.get('url') else ''}
                        </div>
                        """, unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"Error displaying analytics: {str(e)}")
                st.info("No post data available for the selected filters.")
    except Exception as e:
        st.error(f"Error in analytics_page: {str(e)}")
        
        # Show a more user-friendly error message
        st.markdown("""
        <div style="background-color: #f8d7da; padding: 15px; border-radius: 5px; margin: 10px 0;">
            <h3 style="margin-top:0; color:#721c24">We encountered an error</h3>
            <p>Our analytics service is currently experiencing some issues. Please try again later.</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("Technical Details (for support)"):
            st.code(str(e), language="python")
            
        if st.button("Return to Dashboard"):
            st.session_state["current_page"] = "Dashboard"
            st.rerun() 