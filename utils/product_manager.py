"""
Product Manager module for the AdBot application.
Handles product data management for ad creation.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union

# Configure logging
logger = logging.getLogger("ProductManager")

class ProductManager:
    """Class for managing product data for advertisements"""
    
    def __init__(self, config):
        """Initialize the product manager with the provided config"""
        self.config = config
        self.products = {}
        self.load_products()
    
    def load_products(self):
        """Load product data from file"""
        try:
            product_file = self.config.product_data_path
            os.makedirs(os.path.dirname(product_file), exist_ok=True)
            
            if os.path.exists(product_file):
                with open(product_file, 'r') as f:
                    self.products = json.load(f)
                logger.info(f"Loaded {len(self.products)} products")
            else:
                self.products = {}
                logger.warning("No product data file found. Starting with empty product list.")
                self.save_products()
        except Exception as e:
            logger.error(f"Error loading products: {str(e)}")
            self.products = {}
    
    def save_products(self):
        """Save product data to file"""
        try:
            product_file = self.config.product_data_path
            os.makedirs(os.path.dirname(product_file), exist_ok=True)
            
            with open(product_file, 'w') as f:
                json.dump(self.products, f, indent=2)
            logger.info(f"Saved {len(self.products)} products")
        except Exception as e:
            logger.error(f"Error saving products: {str(e)}")
    
    def get_all_products(self) -> Dict:
        """Get all products"""
        return self.products
    
    def get_product(self, product_id: str) -> Dict:
        """Get a product by ID"""
        if product_id in self.products:
            return self.products[product_id]
        return None
    
    def add_product(self, product_data: Dict) -> str:
        """Add a new product"""
        try:
            # Generate a new product ID if not provided
            if "id" not in product_data:
                product_id = f"PROD_{len(self.products) + 1}"
                product_data["id"] = product_id
            else:
                product_id = product_data["id"]
            
            # Ensure required fields are present
            required_fields = ["name", "description", "features", "target_audience"]
            for field in required_fields:
                if field not in product_data:
                    return f"Missing required field: {field}"
            
            # Add the product
            self.products[product_id] = product_data
            self.save_products()
            
            logger.info(f"Added product: {product_id} - {product_data['name']}")
            return product_id
        except Exception as e:
            logger.error(f"Error adding product: {str(e)}")
            return f"Error: {str(e)}"
    
    def update_product(self, product_id: str, product_data: Dict) -> bool:
        """Update an existing product"""
        try:
            if product_id not in self.products:
                logger.error(f"Product not found: {product_id}")
                return False
            
            # Update the product data
            current_data = self.products[product_id]
            for key, value in product_data.items():
                current_data[key] = value
            
            # Ensure ID doesn't change
            current_data["id"] = product_id
            
            self.save_products()
            
            logger.info(f"Updated product: {product_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating product: {str(e)}")
            return False
    
    def delete_product(self, product_id: str) -> bool:
        """Delete a product"""
        try:
            if product_id not in self.products:
                logger.error(f"Product not found: {product_id}")
                return False
            
            # Remove the product
            del self.products[product_id]
            self.save_products()
            
            logger.info(f"Deleted product: {product_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting product: {str(e)}")
            return False
    
    def search_products(self, query: str) -> List[Dict]:
        """Search for products based on a query string"""
        try:
            results = []
            query = query.lower()
            
            for product_id, product in self.products.items():
                # Search in name, description, and features
                if query in product.get("name", "").lower() or \
                   query in product.get("description", "").lower() or \
                   any(query in feature.lower() for feature in product.get("features", [])):
                    # Add product ID for reference
                    product_copy = product.copy()
                    product_copy["id"] = product_id
                    results.append(product_copy)
            
            return results
        except Exception as e:
            logger.error(f"Error searching products: {str(e)}")
            return []
    
    def get_product_categories(self) -> List[str]:
        """Get a list of all product categories"""
        categories = set()
        
        for product in self.products.values():
            if "category" in product:
                categories.add(product["category"])
        
        return sorted(list(categories))
    
    def get_products_by_category(self, category: str) -> List[Dict]:
        """Get all products in a specific category"""
        results = []
        
        for product_id, product in self.products.items():
            if product.get("category") == category:
                # Add product ID for reference
                product_copy = product.copy()
                product_copy["id"] = product_id
                results.append(product_copy)
        
        return results 