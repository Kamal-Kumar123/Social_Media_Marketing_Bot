"""
Payment pages for the AdBot application.
"""

import streamlit as st
import pandas as pd
import datetime
import plotly.express as px

def billing_page(payment_manager, auth_manager):
    """Display billing and payment page"""
    st.title("Billing & Subscription")
    
    user = auth_manager.get_current_user()
    company = auth_manager.get_current_company()
    
    if not user or not company:
        st.warning("Please log in to access billing information")
        return
    
    # Get company payment data
    payment_data = payment_manager.get_payment_page(company["id"])
    
    if "error" in payment_data:
        st.error(f"Error loading payment data: {payment_data['error']}")
        
        # Still show basic information even when there's an error
        st.markdown("### Basic Information")
        st.info(f"Using fallback data since there was an error retrieving your full billing information.")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Current Plan:** {payment_data['company'].get('plan', 'Free').capitalize()}")
        with col2:
            st.markdown(f"**Credit Balance:** ${payment_data['balance'].get('balance', 0):.2f}")
        
        # Add credits form
        st.markdown("### Add Credits")
        
        if st.button("Add $10 Credits"):
            _handle_add_funds(payment_manager, company["id"], 10)
        
        return
    
    # Tabs for different billing sections
    tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Add Credits", "Usage", "Plans"])
    
    with tab1:
        _display_billing_overview(payment_data, company)
    
    with tab2:
        _display_add_credits(payment_manager, company["id"])
    
    with tab3:
        _display_usage_history(payment_data)
    
    with tab4:
        _display_subscription_plans(payment_manager, payment_data, company["id"])

def _display_billing_overview(payment_data, company):
    """Display billing overview section"""
    st.markdown("### Billing Overview")
    
    # Current plan
    plan = company.get("plan", "free")
    plan_details = payment_data["plans"].get(plan, {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**Current Plan:** {plan_details.get('name', plan.capitalize())}")
        if plan != "free" and "stripe_subscription_id" in company:
            st.markdown(f"**Subscription ID:** {company.get('stripe_subscription_id', 'Unknown')}")
            
            if company.get("cancellation_requested"):
                st.warning(f"Your subscription will end on: {company.get('cancels_at', 'Unknown date')}")
    
    with col2:
        # Credit balance
        balance = payment_data.get("balance", {}).get("balance", 0)
        st.markdown(f"**Credit Balance:** ${balance:.2f}")
        
        if balance < 5:
            st.warning("Your credit balance is low. Consider adding more credits.")
    
    # Payment methods
    st.markdown("### Payment Methods")
    payment_methods = payment_data.get("payment_methods", [])
    
    if not payment_methods:
        st.info("No payment methods added yet. Add one in the 'Add Credits' tab.")
    else:
        for method in payment_methods:
            method_type = method.get("type", "unknown")
            is_default = "✓ Default" if method.get("is_default") else ""
            
            if method_type == "card":
                st.markdown(
                    f"**{method.get('brand', '').title()} •••• {method.get('last_four', 'xxxx')}** {is_default}"
                )

def _display_add_credits(payment_manager, company_id):
    """Display add credits section"""
    st.markdown("### Add Credits")
    st.markdown("Add funds to your pay-as-you-go account for usage beyond your plan limits.")
    
    # Preset amounts
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("$10", key="add_10"):
            _handle_add_funds(payment_manager, company_id, 10)
    
    with col2:
        if st.button("$20", key="add_20"):
            _handle_add_funds(payment_manager, company_id, 20)
    
    with col3:
        if st.button("$50", key="add_50"):
            _handle_add_funds(payment_manager, company_id, 50)
    
    # Custom amount
    st.markdown("#### Custom Amount")
    amount = st.number_input("Amount ($)", min_value=5.0, max_value=1000.0, value=20.0, step=5.0)
    
    if st.button("Add Funds", key="add_custom"):
        _handle_add_funds(payment_manager, company_id, amount)
    
    # Add payment method
    st.markdown("### Add Payment Method")
    st.markdown("This section would typically integrate with Stripe Elements for secure card collection.")
    st.info("Note: In a production app, card details would be collected securely using Stripe Elements.")

def _handle_add_funds(payment_manager, company_id, amount):
    """Handle add funds button click"""
    try:
        # Create checkout session
        result = payment_manager.create_checkout_session(company_id, amount)
        
        if "error" in result:
            st.error(f"Error creating checkout: {result['error']}")
        elif "url" in result:
            st.markdown(f"[Click here to complete payment](result['url'])")
            st.info("You'll be redirected to Stripe to complete the payment securely.")
    except Exception as e:
        st.error(f"Error processing payment: {str(e)}")

def _display_usage_history(payment_data):
    """Display usage history section"""
    st.markdown("### Usage History")
    
    usage_history = payment_data.get("usage_history", [])
    
    if not usage_history:
        st.info("No usage history found.")
        return
    
    # Create dataframe from usage history
    usage_data = []
    for item in usage_history:
        usage_data.append({
            "Date": item.get("timestamp", "").split("T")[0] if isinstance(item.get("timestamp"), str) else "Unknown",
            "Type": item.get("type", "Unknown"),
            "Quantity": item.get("quantity", 0),
            "Cost": f"${item.get('cost', 0):.2f}"
        })
    
    if usage_data:
        st.dataframe(usage_data)
        
        # Create usage visualization
        if len(usage_data) > 1:
            st.markdown("### Usage Trends")
            
            # Group by date and type, calculate costs
            df = pd.DataFrame(usage_history)
            
            if "timestamp" in df.columns:
                df["date"] = pd.to_datetime(df["timestamp"]).dt.date
                
                # Create date histogram of costs
                date_costs = df.groupby("date")["cost"].sum().reset_index()
                
                fig = px.bar(
                    date_costs, 
                    x="date", 
                    y="cost",
                    title="Daily Usage Costs",
                    labels={"date": "Date", "cost": "Cost ($)"}
                )
                st.plotly_chart(fig)

def _display_subscription_plans(payment_manager, payment_data, company_id):
    """Display subscription plans section"""
    st.markdown("### Subscription Plans")
    
    plans = payment_data.get("plans", {})
    current_plan = payment_data.get("company", {}).get("plan", "free")
    
    # Create plan comparison table
    st.markdown("#### Plan Comparison")
    
    # Extract plan features for comparison
    plan_features = []
    for plan_id, plan in plans.items():
        plan_feature = {
            "Plan": plan.get("name", plan_id.capitalize()),
            "Price": f"${plan.get('price', 0):.2f}/month" if "price" in plan else "Free",
            "Posts": plan.get("monthly_posts", 0),
            "Platforms": plan.get("platforms", 0),
            "Analytics": "✓" if plan.get("analytics") else "✗",
            "Scheduling": "✓" if plan.get("schedule") else "✗",
            "Team Members": plan.get("team_members", 0)
        }
        plan_features.append(plan_feature)
    
    # Display as dataframe
    st.dataframe(plan_features)
    
    # Display current plan and upgrade options
    st.markdown(f"**Current Plan:** {plans.get(current_plan, {}).get('name', current_plan.capitalize())}")
    
    # Upgrade buttons
    st.markdown("#### Upgrade Plan")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if current_plan != "starter" and "starter" in plans:
            if st.button("Upgrade to Starter"):
                _handle_plan_upgrade(payment_manager, company_id, "starter")
    
    with col2:
        if current_plan not in ["business", "enterprise"] and "business" in plans:
            if st.button("Upgrade to Business"):
                _handle_plan_upgrade(payment_manager, company_id, "business")
    
    with col3:
        if current_plan != "enterprise" and "enterprise" in plans:
            if st.button("Upgrade to Enterprise"):
                _handle_plan_upgrade(payment_manager, company_id, "enterprise")
    
    # Downgrade or cancel
    if current_plan != "free":
        st.markdown("#### Cancel Subscription")
        st.warning("Cancelling your subscription will downgrade to the free plan at the end of your billing period.")
        
        if st.button("Cancel Subscription"):
            result = payment_manager.cancel_subscription(company_id)
            
            if "error" in result:
                st.error(f"Error cancelling subscription: {result['error']}")
            else:
                st.success("Your subscription has been cancelled and will end at the end of your billing period.")

def _handle_plan_upgrade(payment_manager, company_id, plan_id):
    """Handle plan upgrade button click"""
    try:
        # Subscribe to plan
        result = payment_manager.subscribe_to_plan(company_id, plan_id)
        
        if "error" in result:
            st.error(f"Error upgrading plan: {result['error']}")
        else:
            st.success(f"Successfully upgraded to {plan_id.capitalize()} plan!")
    except Exception as e:
        st.error(f"Error upgrading plan: {str(e)}") 