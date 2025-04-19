"""
Product management pages for the AdBot application.
"""

import streamlit as st
import time
import pandas as pd

def products_page(data_access, auth_manager):
    """Product management page"""
    st.title("Product Management")
    
    # Get current company
    user = auth_manager.get_current_user()
    company = auth_manager.get_current_company()
    
    if not user or not company:
        st.warning("Please log in to manage products")
        return
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["Product List", "Add Product", "Edit Product"])
    
    with tab1:
        _product_list_tab(data_access, company["id"])
    
    with tab2:
        _add_product_tab(data_access, company["id"])
    
    with tab3:
        _edit_product_tab(data_access, company["id"])

def _product_list_tab(data_access, company_id):
    """Display product list tab"""
    st.markdown("### Your Products")
    
    # Get products for company
    products = data_access.get_company_products(company_id)
    
    if not products:
        st.info("No products found. Add some products to get started.")
    else:
        # Convert to list for table display
        product_list = []
        for product_id, product_data in products.items():
            product_list.append({
                "ID": product_id,
                "Name": product_data.get("name", ""),
                "Category": product_data.get("category", ""),
                "Target Audience": product_data.get("target_audience", "")
            })
        
        df = pd.DataFrame(product_list)
        st.dataframe(df)
        
        # Product details
        st.markdown("### Product Details")
        selected_product_id = st.selectbox("Select a product to view details:", list(products.keys()))
        
        if selected_product_id:
            product = products[selected_product_id]
            
            st.markdown(f"**Name:** {product.get('name', '')}")
            st.markdown(f"**Category:** {product.get('category', '')}")
            st.markdown(f"**Target Audience:** {product.get('target_audience', '')}")
            st.markdown(f"**Description:**")
            st.write(product.get('description', ''))
            
            st.markdown("**Key Features:**")
            for feature in product.get('features', []):
                st.write(f"- {feature}")
            
            # Actions
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Create Ad", key="create_ad_for_product"):
                    st.session_state["selected_product_for_ad"] = selected_product_id
                    st.session_state["current_page"] = "Create Ad"
                    st.rerun()
            
            with col2:
                if st.button("Delete Product", key="delete_product"):
                    if data_access.delete_product(selected_product_id, company_id):
                        st.success(f"Product {selected_product_id} deleted successfully.")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Failed to delete product.")

def _add_product_tab(data_access, company_id):
    """Display add product tab"""
    st.markdown("### Add New Product")
    
    # Product form
    with st.form("add_product_form"):
        name = st.text_input("Product Name")
        category = st.text_input("Category")
        description = st.text_area("Description")
        features_text = st.text_area("Features (one per line)")
        target_audience = st.text_input("Target Audience")
        
        submitted = st.form_submit_button("Add Product")
        
        if submitted:
            if not name or not description or not features_text or not target_audience:
                st.error("All fields are required.")
            else:
                # Parse features
                features = [f.strip() for f in features_text.split('\n') if f.strip()]
                
                # Create product data
                product_data = {
                    "name": name,
                    "category": category,
                    "description": description,
                    "features": features,
                    "target_audience": target_audience
                }
                
                # Add product
                product_id = data_access.add_product(product_data, company_id)
                
                if product_id:
                    st.success(f"Product added successfully with ID: {product_id}")
                    
                    # Log event
                    data_access.log_event(
                        "product_created", 
                        {"product_id": product_id}, 
                        company_id, 
                        st.session_state.get("user", {}).get("id")
                    )
                    
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Failed to add product.")

def _edit_product_tab(data_access, company_id):
    """Display edit product tab"""
    st.markdown("### Edit Product")
    
    # Get products for company
    products = data_access.get_company_products(company_id)
    
    if not products:
        st.info("No products available to edit.")
    else:
        edit_product_id = st.selectbox("Select a product to edit:", list(products.keys()))
        
        if edit_product_id:
            product = products[edit_product_id]
            
            with st.form("edit_product_form"):
                name = st.text_input("Product Name", value=product.get("name", ""))
                category = st.text_input("Category", value=product.get("category", ""))
                description = st.text_area("Description", value=product.get("description", ""))
                features_text = st.text_area("Features (one per line)", value="\n".join(product.get("features", [])))
                target_audience = st.text_input("Target Audience", value=product.get("target_audience", ""))
                
                submit_edit = st.form_submit_button("Update Product")
                
                if submit_edit:
                    if not name or not description or not features_text or not target_audience:
                        st.error("All fields are required.")
                    else:
                        # Parse features
                        features = [f.strip() for f in features_text.split('\n') if f.strip()]
                        
                        # Create updated product data
                        updated_product_data = {
                            "name": name,
                            "category": category,
                            "description": description,
                            "features": features,
                            "target_audience": target_audience
                        }
                        
                        # Update product
                        if data_access.update_product(edit_product_id, updated_product_data, company_id):
                            st.success(f"Product {edit_product_id} updated successfully.")
                            
                            # Log event
                            data_access.log_event(
                                "product_updated", 
                                {"product_id": edit_product_id}, 
                                company_id, 
                                st.session_state.get("user", {}).get("id")
                            )
                            
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Failed to update product.") 