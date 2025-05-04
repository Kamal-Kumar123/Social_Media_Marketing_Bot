"""
Ad creation and scheduling pages for the AdBot application.
"""

import streamlit as st
import time
import datetime
import pandas as pd
import traceback

def create_ad_page(data_access, auth_manager, content_generator, social_handler, payment_manager):
    """Page for creating social media ads"""
    try:
        st.title("Create Ad")
        
        # Get user and company
        user = auth_manager.get_current_user()
        company = auth_manager.get_current_company()
        
        if not user or not company:
            st.warning("Please log in to access this page")
            return
        
        # Display debugging info
        st.sidebar.markdown("### Debug Info")
        with st.sidebar.expander("User & Company"):
            st.json({"user": user, "company": company})
        
        # Get company products
        try:
            products = data_access.get_company_products(company["id"])
            with st.sidebar.expander("Products"):
                st.json(products)
        except Exception as e:
            st.error(f"Error loading products: {str(e)}")
            products = {}
        
        if not products:
            st.warning("You need to add products before creating ads.")
            
            if st.button("Go to Products Page"):
                st.session_state["current_page"] = "Products"
                st.rerun()
            return
        
        # Check if we're coming from the products page with a pre-selected product
        default_product = None
        if "selected_product_for_ad" in st.session_state:
            default_product = st.session_state["selected_product_for_ad"]
            del st.session_state["selected_product_for_ad"]
        
        # If no product is selected yet, show the product selection form
        if "selected_product" not in st.session_state:
            st.subheader("Select a Product")
            
            with st.form("product_selection_form"):
                # Select product
                try:
                    product_id = st.selectbox(
                        "Select Product", 
                        options=list(products.keys()),
                        format_func=lambda x: f"{x} - {products[x]['name']}",
                        index=list(products.keys()).index(default_product) if default_product in products else 0
                    )
                except Exception as e:
                    st.error(f"Error displaying product selection: {str(e)}")
                    product_id = None
                
                # Submit button
                if st.form_submit_button("Select Product"):
                    if product_id:
                        st.session_state["selected_product"] = product_id
                        st.rerun()
                    else:
                        st.error("No product selected or product list is empty")
            return
        
        # Get the selected product
        product_id = st.session_state["selected_product"]
        if product_id not in products:
            st.error("Selected product not found. Please select another product.")
            del st.session_state["selected_product"]
            st.rerun()
            return
        
        # Form for ad creation
        with st.form("create_ad_form"):
            st.markdown("### Ad Details")
            
            # Show selected product
            st.info(f"Selected Product: {products[product_id]['name']}")
            
            # Provide option to change product
            if st.form_submit_button("Change Product"):
                del st.session_state["selected_product"]
                st.rerun()
                return
            
            # Get company plan
            plan = company.get("plan", "free")
            plan_details = payment_manager.plans.get(plan, {})
            plan_limit_reached = False
            
            # Check if reached limit for current plan (simplified for example)
            if plan == "free":
                # Check if free tier limit reached
                current_month_start = datetime.datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                current_posts = data_access.db.collection("posts").where(
                    "company_id", "==", company["id"]
                ).where(
                    "timestamp", ">=", current_month_start.isoformat()
                ).get()
                
                free_limit = 10  # Same as in payment_manager.plans["free"]["monthly_posts"]
                if len(current_posts) >= free_limit:
                    plan_limit_reached = True
                    st.warning(f"You have reached your monthly post limit ({free_limit}) for the free plan. Upgrade your plan or add credits to continue.")
            
            # Select platform 
            available_platforms = ["facebook", "twitter", "instagram", "linkedin", "tiktok", "pinterest"]
            
            # Limit platforms based on plan
            # if plan == "free":
            #     available_platforms = available_platforms[:2]  # First 2 platforms

            #  #######edit below#######  #


            # if plan == "starter":
            #     available_platforms = available_platforms[:3]  # First 3 platforms
            # elif plan == "business":
            #     available_platforms = available_platforms[:5]  # First 5 platforms
            

            st.title("Select Platforms")
            # create a dictionary to store checkbox state
            Selected_Platforms = { }
            
            # Create checkboxes for each entity
            for Platform in available_platforms:
                Selected_Platforms[Platform] = st.checkbox(Platform)
            
            # Ad format
            format_type = st.radio(
                "Ad Format",
                options=["image"],
                horizontal=True
            )
            
            # Ad tone
            tone = st.select_slider(
                "Ad Tone",
                options=["professional", "conversational", "humorous", "serious", "dramatic"]
            )
            
            # Add text input for ad copy
            st.markdown("### Ad Copy")
            ad_copy = st.text_area(
                "Enter your ad text",
                placeholder="Enter the text content for your advertisement here...",
                height=150
            )
            
            # Add image upload functionality
            st.markdown("### Ad Image")
            uploaded_image = st.file_uploader("Upload an image for your ad", type=["jpg", "jpeg", "png"])
            
            # Display uploaded image preview
            if uploaded_image is not None:
                st.image(uploaded_image, caption="Uploaded Image", use_column_width=True)
            
            # Ad length
            length = st.select_slider(
                "Ad Length",
                options=["short", "medium", "long"]
            )
            
            # Generate or post
            col1, col2 = st.columns(2)
            with col1:
                preview = st.form_submit_button("Generate Preview", disabled=plan_limit_reached)
            
            with col2:
                post_now = st.form_submit_button("Post Now", disabled=plan_limit_reached)
        
        # Handle generate preview
        if preview:
            st.markdown("### Ad Preview")
            
            with st.spinner("Generating ad content..."):
                try:
                    # Get product data
                    product = products[product_id]
                    
                    # Get the selected platform from checkboxes
                    selected_platform_list = [p for p, is_selected in Selected_Platforms.items() if is_selected]
                    
                    if not selected_platform_list:
                        st.error("Please select at least one platform to generate ad content")
                        return
                    
                    # Use the first selected platform
                    platform = selected_platform_list[0]
                    
                    # Check if user provided ad copy
                    if not ad_copy:
                        st.error("Please enter ad copy text for your advertisement")
                        return
                    
                    # Record usage for image generation (check balance)
                    usage_result = payment_manager.record_usage(company["id"], "image_generation")
                    
                    if "error" in usage_result and not usage_result.get("success", False):
                        st.error(f"Cannot generate content: {usage_result['error']}")
                        st.info("Please add credits to your account to continue using the service.")
                        return
                    
                    # Create ad content from user inputs instead of generating
                    ad_content = {
                        "platform": platform,
                        "copy": ad_copy,
                        "product_id": product_id,
                        "format_type": format_type
                    }
                    
                    # Handle image upload
                    if uploaded_image is not None:
                        # Save the uploaded image to a file
                        import os
                        from PIL import Image
                        import io
                        
                        # Create directory if it doesn't exist
                        os.makedirs("data/images", exist_ok=True)
                        
                        # Generate a unique filename
                        image_filename = f"data/images/{company['id']}_{product_id}_{int(time.time())}.jpg"
                        
                        # Save the image
                        img = Image.open(uploaded_image)
                        img.save(image_filename)
                        
                        # Add image path to ad_content
                        ad_content["image_path"] = image_filename
                    
                    # Store in session state for posting
                    st.session_state["current_ad_content"] = ad_content
                    
                    # Display preview
                    st.markdown("#### Ad Copy")
                    st.markdown(ad_content["copy"])
                    
                    if "hashtags" in ad_content:
                        st.markdown("#### Hashtags")
                        st.markdown(" ".join(ad_content["hashtags"]))
                    
                    if "image_path" in ad_content:
                        st.markdown("#### Ad Image")
                        st.image(ad_content["image_path"])
                    elif uploaded_image is not None:
                        st.markdown("#### Ad Image")
                        st.image(uploaded_image)
                    
                    # Post button
                    if st.button("Post This Ad"):
                        # Get the selected platform from checkboxes
                        selected_platform_list = [p for p, is_selected in Selected_Platforms.items() if is_selected]
                        
                        if not selected_platform_list:
                            st.error("Please select at least one platform to post to")
                            return
                        
                        # Use the first selected platform (or we could loop through all selected)
                        platform = selected_platform_list[0]
                        
                        with st.spinner("Posting to " + platform + "..."):
                            # Record usage for post
                            usage_result = payment_manager.record_usage(company["id"], "post")
                            
                            if "error" in usage_result and not usage_result.get("success", False):
                                st.error(f"Cannot post content: {usage_result['error']}")
                                st.info("Please add credits to your account to continue using the service.")
                                return
                            
                            # Add company_id to ad_content
                            ad_content["company_id"] = company["id"]
                            
                            # Post to platform
                            post_result = social_handler.post_ad(ad_content)
                            
                            if post_result["success"]:
                                # Record post in database
                                post_id = data_access.record_post(
                                    {
                                        "platform": platform,
                                        "product_id": product_id,
                                        "format_type": format_type,
                                        "company_id": company["id"],
                                        "user_id": user["id"],
                                        "content": {
                                            "copy": ad_content["copy"],
                                            "hashtags": ad_content.get("hashtags", []),
                                            "image_path": ad_content.get("image_path", "")
                                        }
                                    },
                                    company["id"]
                                )
                                
                                st.success(f"Posted successfully to {platform}! Post ID: {post_result['post_id']}")
                                
                                # Log event
                                data_access.log_event(
                                    "post_created", 
                                    {"post_id": post_id, "platform": platform, "product_id": product_id}, 
                                    company["id"], 
                                    user["id"]
                                )
                            else:
                                st.error(f"Failed to post: {post_result.get('error', 'Unknown error')}")
                
                except Exception as e:
                    error_details = traceback.format_exc()
                    st.error(f"Error generating ad preview: {str(e)}")
                    st.expander("Error details").code(error_details)
        
        # Handle post now
        if post_now:
            try:
                # Get the selected platform from checkboxes
                selected_platform_list = [p for p, is_selected in Selected_Platforms.items() if is_selected]
                
                if not selected_platform_list:
                    st.error("Please select at least one platform to post to")
                    return
                
                # Check if user provided ad copy
                if not ad_copy:
                    st.error("Please enter ad copy text for your advertisement")
                    return
                
                # Use the first selected platform
                platform = selected_platform_list[0]
                
                with st.spinner(f"Creating and posting ad to {platform}..."):
                    # Get product data
                    product = products[product_id]
                    
                    # Record usage for post and image generation
                    image_usage_result = payment_manager.record_usage(company["id"], "image_generation")
                    post_usage_result = payment_manager.record_usage(company["id"], "post")
                    
                    if (("error" in image_usage_result and not image_usage_result.get("success", False)) or
                        ("error" in post_usage_result and not post_usage_result.get("success", False))):
                        st.error("Cannot post: Insufficient credits")
                        st.info("Please add credits to your account to continue using the service.")
                        return
                    
                    # Create ad content from user inputs instead of generating
                    ad_content = {
                        "platform": platform,
                        "copy": ad_copy,
                        "product_id": product_id,
                        "format_type": format_type
                    }
                    
                    # Handle image upload
                    if uploaded_image is not None:
                        # Save the uploaded image to a file
                        import os
                        from PIL import Image
                        import io
                        
                        # Create directory if it doesn't exist
                        os.makedirs("data/images", exist_ok=True)
                        
                        # Generate a unique filename
                        image_filename = f"data/images/{company['id']}_{product_id}_{int(time.time())}.jpg"
                        
                        # Save the image
                        img = Image.open(uploaded_image)
                        img.save(image_filename)
                        
                        # Add image path to ad_content
                        ad_content["image_path"] = image_filename
                    
                    # Add company_id to ad_content
                    ad_content["company_id"] = company["id"]
                    
                    # Post to platform
                    post_result = social_handler.post_ad(ad_content)
                    
                    if post_result["success"]:
                        # Record post in database
                        post_id = data_access.record_post(
                            {
                                "platform": platform,
                                "product_id": product_id,
                                "format_type": format_type,
                                "company_id": company["id"],
                                "user_id": user["id"],
                                "content": {
                                    "copy": ad_content["copy"],
                                    "hashtags": ad_content.get("hashtags", []),
                                    "image_path": ad_content.get("image_path", "")
                                }
                            },
                            company["id"]
                        )
                        
                        st.success(f"Posted successfully to {platform}! Post ID: {post_result['post_id']}")
                        
                        # Log event
                        data_access.log_event(
                            "post_created", 
                            {"post_id": post_id, "platform": platform, "product_id": product_id}, 
                            company["id"], 
                            user["id"]
                        )
                    else:
                        st.error(f"Failed to post: {post_result.get('error', 'Unknown error')}")
                
            except Exception as e:
                error_details = traceback.format_exc()
                st.error(f"Error posting ad: {str(e)}")
                st.expander("Error details").code(error_details)

    except Exception as e:
        error_details = traceback.format_exc()
        st.error(f"Error in create_ad_page: {str(e)}")
        st.markdown("### Debug Information")
        st.markdown("If this error persists, please contact support with the following details:")
        st.expander("Error details").code(error_details)

def schedule_page(data_access, auth_manager, scheduler, payment_manager):
    """Post scheduling page"""
    st.title("Schedule Posts")
    
    # Get user and company
    user = auth_manager.get_current_user()
    company = auth_manager.get_current_company()
    
    if not user or not company:
        st.warning("Please log in to schedule posts")
        return
    
    # Check if scheduling is allowed on current plan
    plan = company.get("plan", "free")
    
    # Get plan details from payment manager (simplified)
    has_scheduling = False
    if plan == "free":
        has_scheduling = False
    else:
        has_scheduling = True
    
    if not has_scheduling:
        st.warning("Scheduling is not available on your current plan. Please upgrade to unlock this feature.")
        return
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["Schedule Posts", "Auto-Schedule", "Scheduled Posts"])
    
    with tab1:
        _schedule_post_tab(data_access, company["id"], user["id"], scheduler, payment_manager)
    
    with tab2:
        _auto_schedule_tab(data_access, company["id"], user["id"], scheduler, payment_manager)
    
    with tab3:
        _scheduled_posts_tab(data_access, company["id"], scheduler)

def _schedule_post_tab(data_access, company_id, user_id, scheduler, payment_manager):
    """Display schedule post tab"""
    st.markdown("### Schedule a Post")
    
    # Get products
    products = data_access.get_company_products(company_id)
    
    if not products:
        st.warning("You need to add products before scheduling posts.")
        return
    
    # Form for scheduling
    with st.form("schedule_post_form"):
        # Select product
        product_id = st.selectbox(
            "Select Product", 
            options=list(products.keys()),
            format_func=lambda x: f"{x} - {products[x]['name']}"
        )
        
        # Select platform
        # In a real app, this would be limited by the company's plan
        available_platforms = ["facebook", "twitter", "instagram", "linkedin", "tiktok", "pinterest"]
        
        platform = st.selectbox(
            "Select Platform",
            options=available_platforms
        )
        
        # Schedule type
        schedule_type = st.radio(
            "Schedule Type",
            options=["One-time", "Recurring"],
            horizontal=True
        )
        
        if schedule_type == "One-time":
            # Date and time for one-time
            schedule_date = st.date_input("Post Date", value=datetime.date.today())
            schedule_time = st.time_input("Post Time", value=datetime.time(12, 0))
            
            recurrence = "once"
        else:
            # Recurrence pattern
            recurrence = st.selectbox(
                "Recurrence Pattern",
                options=["daily", "weekly", "monthly"]
            )
            
            # Time for recurring
            schedule_time = st.time_input("Post Time", value=datetime.time(12, 0))
        
        # Ad format
        format_type = st.radio(
            "Ad Format",
            options=["image"],
            horizontal=True
        )
        
        # Submit
        submitted = st.form_submit_button("Schedule Post")
        
        if submitted:
            try:
                # Check if user has enough credits for a scheduled post
                usage_result = payment_manager.record_usage(company_id, "scheduled_post")
                
                if "error" in usage_result and not usage_result.get("success", False):
                    st.error(f"Cannot schedule post: {usage_result['error']}")
                    st.info("Please add credits to your account to continue using the service.")
                    return
                
                # Format schedule time based on type
                if schedule_type == "One-time":
                    schedule_dt = datetime.datetime.combine(schedule_date, schedule_time)
                    schedule_time_str = f"date:{schedule_dt.strftime('%Y-%m-%d %H:%M')}"
                else:
                    schedule_time_str = f"at:{schedule_time.strftime('%H:%M')}"
                
                # Create schedule data
                schedule_data = {
                    "product_id": product_id,
                    "platform": platform,
                    "schedule_time": schedule_time_str,
                    "format_type": format_type,
                    "recurrence": recurrence,
                    "company_id": company_id,
                    "user_id": user_id,
                    "status": "scheduled"
                }
                
                # Add schedule
                schedule_id = data_access.add_schedule(schedule_data, company_id)
                
                if schedule_id:
                    # Add to scheduler
                    scheduler._add_to_schedule({
                        "id": schedule_id,
                        **schedule_data
                    })
                    
                    st.success(f"Post scheduled successfully! Schedule ID: {schedule_id}")
                    
                    # Log event
                    data_access.log_event(
                        "post_scheduled", 
                        {"schedule_id": schedule_id, "platform": platform, "product_id": product_id}, 
                        company_id, 
                        user_id
                    )
                else:
                    st.error("Failed to schedule post")
                    
            except Exception as e:
                st.error(f"Error scheduling post: {str(e)}")

def _auto_schedule_tab(data_access, company_id, user_id, scheduler, payment_manager):
    """Display auto-schedule tab"""
    st.markdown("### Auto-Schedule Posts")
    
    # Get products
    products = data_access.get_company_products(company_id)
    
    if not products:
        st.warning("You need to add products before auto-scheduling posts.")
        return
    
    # Form for auto-scheduling
    with st.form("auto_schedule_form"):
        # Select product
        product_id = st.selectbox(
            "Select Product",
            options=list(products.keys()),
            format_func=lambda x: f"{x} - {products[x]['name']}",
            key="auto_product"
        )
        
        # Select platforms
        available_platforms = ["facebook", "twitter", "instagram", "linkedin", "tiktok", "pinterest"]
        
        selected_platforms = st.multiselect(
            "Select Platforms (leave empty for all)",
            options=available_platforms
        )
        
        # Schedule duration
        days = st.slider("Number of Days", 1, 30, 7)
        
        # Posts per day
        posts_per_day = st.slider("Posts Per Day", 1, 5, 2)
        
        # Submit
        auto_submitted = st.form_submit_button("Auto-Schedule Posts")
        
        if auto_submitted:
            try:
                # Check if user has enough credits
                total_posts = days * posts_per_day
                usage_result = payment_manager.record_usage(company_id, "scheduled_post", total_posts)
                
                if "error" in usage_result and not usage_result.get("success", False):
                    st.error(f"Cannot auto-schedule posts: {usage_result['error']}")
                    st.info("Please add credits to your account to continue using the service.")
                    return
                
                platforms = selected_platforms if selected_platforms else available_platforms
                
                # Create schedules for each day
                schedule_ids = []
                
                for day in range(days):
                    day_date = datetime.datetime.now() + datetime.timedelta(days=day)
                    
                    # Create posts for this day
                    for post_num in range(posts_per_day):
                        # Pick a platform for this post
                        platform = platforms[post_num % len(platforms)]
                        
                        # Generate a random time (9 AM to 7 PM)
                        hour = 9 + (post_num * 8 // posts_per_day)  # Distribute throughout the day
                        minute = (post_num * 60 // posts_per_day) % 60
                        
                        schedule_time = f"date:{day_date.strftime('%Y-%m-%d')} {hour:02d}:{minute:02d}"
                        
                        # Create schedule data
                        schedule_data = {
                            "product_id": product_id,
                            "platform": platform,
                            "schedule_time": schedule_time,
                            "format_type": "image",
                            "recurrence": "once",
                            "company_id": company_id,
                            "user_id": user_id,
                            "status": "scheduled"
                        }
                        
                        # Add schedule
                        schedule_id = data_access.add_schedule(schedule_data, company_id)
                        
                        if schedule_id:
                            # Add to scheduler
                            scheduler._add_to_schedule({
                                "id": schedule_id,
                                **schedule_data
                            })
                            
                            schedule_ids.append(schedule_id)
                
                if schedule_ids:
                    st.success(f"Auto-scheduled {len(schedule_ids)} posts successfully!")
                    
                    # Log event
                    data_access.log_event(
                        "posts_auto_scheduled", 
                        {"count": len(schedule_ids), "product_id": product_id}, 
                        company_id, 
                        user_id
                    )
                else:
                    st.error("Failed to auto-schedule posts")
                
            except Exception as e:
                st.error(f"Error auto-scheduling posts: {str(e)}")

def _scheduled_posts_tab(data_access, company_id, scheduler):
    """Display scheduled posts tab"""
    st.markdown("### Scheduled Posts")
    
    # Get all schedules for the company
    schedules = data_access.get_company_schedules(company_id)
    
    if not schedules:
        st.info("No scheduled posts found.")
    else:
        # Filter options
        status_filter = st.multiselect(
            "Filter by Status",
            options=["scheduled", "completed", "failed", "cancelled"],
            default=["scheduled"]
        )
        
        # Convert to dataframe
        schedule_list = []
        for schedule_id, schedule_data in schedules.items():
            if status_filter and schedule_data.get("status") not in status_filter:
                continue
                
            # Get product details
            product_id = schedule_data.get("product_id")
            product = data_access.get_product(product_id, company_id)
            product_name = product.get("name", "Unknown") if product else "Unknown"
            
            schedule_list.append({
                "ID": schedule_id,
                "Product": f"{product_id} - {product_name}",
                "Platform": schedule_data.get("platform", ""),
                "Schedule Time": schedule_data.get("schedule_time", ""),
                "Recurrence": schedule_data.get("recurrence", ""),
                "Status": schedule_data.get("status", ""),
                "Created At": schedule_data.get("created_at", "").split("T")[0] if isinstance(schedule_data.get("created_at"), str) else ""
            })
        
        if schedule_list:
            df = pd.DataFrame(schedule_list)
            st.dataframe(df)
            
            # Cancel schedules
            st.markdown("### Cancel Scheduled Posts")
            
            scheduled_ids = [s["ID"] for s in schedule_list if s["Status"] == "scheduled"]
            
            if scheduled_ids:
                cancel_id = st.selectbox(
                    "Select Schedule to Cancel",
                    options=scheduled_ids
                )
                
                if cancel_id and st.button("Cancel Selected Schedule"):
                    # Update schedule status
                    schedule_data = {"status": "cancelled"}
                    
                    if data_access.update_schedule(cancel_id, schedule_data, company_id):
                        st.success(f"Schedule {cancel_id} cancelled successfully.")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Failed to cancel schedule.")
            else:
                st.info("No active schedules to cancel.") 