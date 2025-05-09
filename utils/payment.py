"""
Payment module for the AdBot application.
Handles Stripe payment processing and subscription management.
"""

import os
import json
import logging
import datetime
import stripe
import firebase_admin
from firebase_admin import credentials, firestore

# Configure logging
logger = logging.getLogger("Payment")

class PaymentManager:
    """Class for handling payments and subscriptions with Stripe"""
    
    def __init__(self):
        """Initialize the payment manager"""
        # Set Stripe API key
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        self.public_key = os.getenv("STRIPE_PUBLIC_KEY")
        
        # Check if we're using a test account - for development but with real posting
        self.test_account = os.getenv("TEST_ACCOUNT", "false").lower() == "true"
        
        # Initialize pricing and usage rates
        self.rates = {
            "post": 0.50,  # $0.50 per post
            "image_generation": 0.25,  # $0.25 per generated image
            "analytics": 0.10,  # $0.10 per analytics report
            "scheduled_post": 0.40,  # $0.40 per scheduled post
        }
        
        # Plans
        self.plans = {
            "free": {
                "name": "Free",
                "monthly_posts": 10,
                "platforms": 2,
                "schedule": False,
                "analytics": False,
                "image_generation": 5,
                "team_members": 1
            },
            "starter": {
                "name": "Starter",
                "price": 29.99,
                "monthly_posts": 50,
                "platforms": 3,
                "schedule": True,
                "analytics": True,
                "image_generation": 20,
                "team_members": 2
            },
            "business": {
                "name": "Business",
                "price": 99.99,
                "monthly_posts": 200,
                "platforms": 5,
                "schedule": True,
                "analytics": True,
                "image_generation": 100,
                "team_members": 5
            },
            "enterprise": {
                "name": "Enterprise",
                "price": 299.99,
                "monthly_posts": "Unlimited",
                "platforms": "All",
                "schedule": True,
                "analytics": True,
                "image_generation": "Unlimited",
                "team_members": "Unlimited"
            }
        }
        
        logger.info(f"PaymentManager initialized - Test Account: {self.test_account}")
    
    def get_payment_page(self, company_id):
        """Get the payment dashboard for a company"""
        try:
            db = firestore.client()
            company_doc = db.collection("companies").document(company_id).get()
            
            if not company_doc.exists:
                logger.error(f"Company not found with ID: {company_id}")
                return {
                    "error": "Company not found",
                    "company": {"plan": "free", "name": "Unknown"},
                    "balance": {"balance": 0.0},
                    "payment_methods": [],
                    "usage_history": [],
                    "rates": self.rates,
                    "plans": self.plans
                }
                
            company = company_doc.to_dict()
            
            # Get current balance and payment methods
            balance = self._get_company_balance(company_id)
            payment_methods = self._get_payment_methods(company_id)
            usage_history = self._get_usage_history(company_id)
            
            return {
                "company": company,
                "balance": balance,
                "payment_methods": payment_methods,
                "usage_history": usage_history,
                "rates": self.rates,
                "plans": self.plans
            }
        except Exception as e:
            logger.error(f"Error getting payment page: {str(e)}")
            return {
                "error": str(e),
                "company": {"plan": "free", "name": "Unknown"},
                "balance": {"balance": 0.0},
                "payment_methods": [],
                "usage_history": [],
                "rates": self.rates,
                "plans": self.plans
            }
    
    def _get_company_balance(self, company_id):
        """Get current balance for a company"""
        try:
            # Special handling for test account - always return a positive balance
            if company_id == "test-company-id":
                return {
                    "balance": 100.0,  # Always maintain a positive balance for test account
                    "last_updated": datetime.datetime.now().isoformat(),
                    "company_id": company_id
                }
            
            # Check if Firebase is initialized
            if not firebase_admin._apps:
                logger.error("Firebase not initialized in PaymentManager")
                return {"balance": 0.0, "error": "Firebase not initialized"}
            
            db = firestore.client()
            balance_doc = db.collection("balances").document(company_id).get()
            
            if not balance_doc.exists:
                # Create initial balance record
                initial_balance = {
                    "balance": 0.0,
                    "last_updated": datetime.datetime.now().isoformat(),
                    "company_id": company_id
                }
                db.collection("balances").document(company_id).set(initial_balance)
                return initial_balance
            
            return balance_doc.to_dict()
        except Exception as e:
            logger.error(f"Error getting company balance: {str(e)}")
            return {"balance": 0.0, "error": str(e)}
    
    def _get_payment_methods(self, company_id):
        """Get saved payment methods for a company"""
        try:
            db = firestore.client()
            methods = db.collection("payment_methods").where("company_id", "==", company_id).get()
            
            payment_methods = []
            for method in methods:
                method_data = method.to_dict()
                payment_methods.append({
                    "id": method.id,
                    **method_data
                })
            
            return payment_methods
        except Exception as e:
            logger.error(f"Error getting payment methods: {str(e)}")
            return []
    
    def _get_usage_history(self, company_id):
        """Get usage history for a company"""
        try:
            db = firestore.client()
            # Get usage data without complex ordering - this avoids needing an index
            history_ref = db.collection("usage").where("company_id", "==", company_id).get()
            
            # Process and sort in Python instead
            usage_items = []
            for item in history_ref:
                item_data = item.to_dict()
                usage_items.append({
                    "id": item.id,
                    **item_data
                })
            
            # Sort by timestamp in Python
            usage_items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            # Limit to 100 items
            return usage_items[:100]
            
        except Exception as e:
            logger.error(f"Error getting usage history: {str(e)}")
            return []
    
    def add_payment_method(self, company_id, token):
        """Add a new payment method from Stripe token"""
        try:
            # Create or get customer in Stripe
            customer_id = self._get_stripe_customer(company_id)
            
            if not customer_id:
                return {"error": "Could not create or find Stripe customer"}
            
            # Add payment method to customer
            payment_method = stripe.PaymentMethod.attach(
                token,
                customer=customer_id
            )
            
            # Make this the default payment method
            stripe.Customer.modify(
                customer_id,
                invoice_settings={
                    "default_payment_method": payment_method.id
                }
            )
            
            # Store payment method info in database
            db = firestore.client()
            db.collection("payment_methods").add({
                "company_id": company_id,
                "stripe_id": payment_method.id,
                "type": payment_method["type"],
                "last_four": payment_method[payment_method["type"]]["last4"],
                "brand": payment_method[payment_method["type"]].get("brand"),
                "is_default": True,
                "created_at": datetime.datetime.now().isoformat()
            })
            
            # Set all other payment methods as non-default
            other_methods = db.collection("payment_methods").where("company_id", "==", company_id).where("is_default", "==", True).get()
            for method in other_methods:
                if method.to_dict().get("stripe_id") != payment_method.id:
                    method.reference.update({"is_default": False})
            
            return {"success": True, "payment_method": payment_method}
        except Exception as e:
            logger.error(f"Error adding payment method: {str(e)}")
            return {"error": str(e)}
    
    def _get_stripe_customer(self, company_id):
        """Get or create a Stripe customer for the company"""
        try:
            db = firestore.client()
            company = db.collection("companies").document(company_id).get().to_dict()
            
            if not company:
                return None
            
            # Check if company already has a Stripe customer ID
            if "stripe_customer_id" in company:
                return company["stripe_customer_id"]
            
            # Get company admin for contact info
            admin_membership = db.collection("company_members").where("company_id", "==", company_id).where("role", "==", "admin").limit(1).get()
            
            if not admin_membership:
                return None
            
            admin_id = admin_membership[0].to_dict().get("user_id")
            admin = db.collection("users").document(admin_id).get().to_dict()
            
            # Create new Stripe customer
            customer = stripe.Customer.create(
                name=company.get("name"),
                email=admin.get("email"),
                metadata={"company_id": company_id}
            )
            
            # Save Stripe customer ID to company
            db.collection("companies").document(company_id).update({
                "stripe_customer_id": customer.id
            })
            
            return customer.id
        except Exception as e:
            logger.error(f"Error getting/creating Stripe customer: {str(e)}")
            return None
    
    def create_checkout_session(self, company_id, amount):
        """Create a Stripe checkout session for adding funds"""
        try:
            # Get Stripe customer
            customer_id = self._get_stripe_customer(company_id)
            
            if not customer_id:
                return {"error": "Could not create or find Stripe customer"}
            
            # Create checkout session
            success_url = os.getenv("STRIPE_SUCCESS_URL", "http://localhost:8501/payment_success?session_id={CHECKOUT_SESSION_ID}")
            cancel_url = os.getenv("STRIPE_CANCEL_URL", "http://localhost:8501/payment_cancel")
            
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'AdBot Credits',
                            'description': f'Add funds to your AdBot account',
                        },
                        'unit_amount': int(amount * 100),  # Convert to cents
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                customer=customer_id,
                metadata={
                    "company_id": company_id,
                    "type": "add_funds",
                    "amount": str(amount)
                }
            )
            
            return {"success": True, "session_id": session.id, "url": session.url}
        except Exception as e:
            logger.error(f"Error creating checkout session: {str(e)}")
            return {"error": str(e)}
    
    def process_webhook(self, payload, sig_header):
        """Process Stripe webhook notifications"""
        try:
            webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
            
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
            
            # Handle specific events
            if event['type'] == 'checkout.session.completed':
                self._handle_checkout_completed(event['data']['object'])
            elif event['type'] == 'payment_intent.succeeded':
                self._handle_payment_succeeded(event['data']['object'])
            
            return {"success": True}
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            return {"error": str(e)}
    
    def _handle_checkout_completed(self, session):
        """Handle completed checkout sessions"""
        try:
            # Extract metadata
            company_id = session.get('metadata', {}).get('company_id')
            amount = float(session.get('metadata', {}).get('amount', 0))
            
            if not company_id or amount <= 0:
                logger.error(f"Invalid checkout session metadata: {session.get('metadata')}")
                return
            
            # Update company balance
            self._add_funds_to_balance(company_id, amount)
            
            # Record transaction
            db = firestore.client()
            db.collection("transactions").add({
                "company_id": company_id,
                "type": "credit",
                "amount": amount,
                "timestamp": datetime.datetime.now().isoformat(),
                "description": "Added funds via Stripe Checkout",
                "stripe_session_id": session.id
            })
        except Exception as e:
            logger.error(f"Error handling checkout completed: {str(e)}")
    
    def _handle_payment_succeeded(self, payment_intent):
        """Handle successful payment intents"""
        try:
            # Record successful payment
            company_id = payment_intent.get('metadata', {}).get('company_id')
            
            if not company_id:
                logger.error(f"Payment intent has no company_id: {payment_intent.id}")
                return
            
            # Update payment status
            db = firestore.client()
            payments = db.collection("payments").where("payment_intent_id", "==", payment_intent.id).get()
            
            for payment in payments:
                payment.reference.update({
                    "status": "succeeded",
                    "updated_at": datetime.datetime.now().isoformat()
                })
        except Exception as e:
            logger.error(f"Error handling payment succeeded: {str(e)}")
    
    def _add_funds_to_balance(self, company_id, amount):
        """Add funds to company balance"""
        try:
            db = firestore.client()
            balance_ref = db.collection("balances").document(company_id)
            balance_doc = balance_ref.get()
            
            if balance_doc.exists:
                balance = balance_doc.to_dict()
                new_balance = balance.get("balance", 0) + amount
                
                balance_ref.update({
                    "balance": new_balance,
                    "last_updated": datetime.datetime.now().isoformat()
                })
            else:
                balance_ref.set({
                    "balance": amount,
                    "last_updated": datetime.datetime.now().isoformat(),
                    "company_id": company_id
                })
            
            logger.info(f"Added ${amount} to company {company_id} balance")
            return True
        except Exception as e:
            logger.error(f"Error adding funds to balance: {str(e)}")
            return False
    
    def record_usage(self, company_id, usage_type, quantity=1):
        """Record usage and deduct from balance if necessary"""
        
        # For test accounts, record usage but don't charge
        if company_id == "test-company-id" or self.test_account:
            logger.info(f"Test account usage recorded for {usage_type} - no charge applied")
            
            try:
                # Record usage for analytics but don't charge
                db = firestore.client()
                usage_ref = db.collection("usage").document()
                usage_data = {
                    "company_id": company_id,
                    "type": usage_type,
                    "quantity": quantity,
                    "amount": 0.0,  # No charge for test accounts
                    "timestamp": datetime.datetime.now().isoformat(),
                    "status": "test_account"
                }
                usage_ref.set(usage_data)
                
                return {
                    "success": True,
                    "message": "Test account usage recorded (no charge)",
                    "id": usage_ref.id
                }
            except Exception as e:
                logger.error(f"Error recording test account usage: {str(e)}")
                # Continue without failing for test accounts
                return {
                    "success": True,
                    "message": f"Test account usage noted but error recording: {str(e)}",
                    "id": None
                }

        # Check if sufficient balance
        if not self._check_sufficient_balance(company_id, usage_type, quantity):
            return {
                "success": False,
                "message": "Insufficient balance"
            }
        
        # If covered by plan, record usage but don't deduct from balance
        if self._is_covered_by_plan(company_id, None, usage_type, quantity):
            try:
                db = firestore.client()
                usage_ref = db.collection("usage").document()
                
                rate = self.rates.get(usage_type, 0.10)  # Default rate if not found
                amount = rate * quantity
                
                usage_data = {
                    "company_id": company_id,
                    "type": usage_type,
                    "quantity": quantity,
                    "amount": amount,
                    "plan_covered": True,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "status": "completed"
                }
                
                usage_ref.set(usage_data)
                
                return {
                    "success": True,
                    "message": "Usage recorded (covered by plan)",
                    "id": usage_ref.id
                }
            except Exception as e:
                logger.error(f"Error recording plan-covered usage: {str(e)}")
                return {
                    "success": False,
                    "message": f"Error recording usage: {str(e)}"
                }
        
        # If not covered by plan, deduct from balance
        try:
            rate = self.rates.get(usage_type, 0.10)  # Default rate if not found
            amount = rate * quantity
            
            # Deduct from balance
            deduction_result = self._deduct_from_balance(company_id, amount)
            
            if not deduction_result["success"]:
                return deduction_result
            
            # Record usage
            db = firestore.client()
            usage_ref = db.collection("usage").document()
            
            usage_data = {
                "company_id": company_id,
                "type": usage_type,
                "quantity": quantity,
                "amount": amount,
                "timestamp": datetime.datetime.now().isoformat(),
                "status": "completed"
            }
            
            usage_ref.set(usage_data)
            
            return {
                "success": True,
                "message": f"Usage recorded and ${amount} deducted from balance",
                "id": usage_ref.id
            }
            
        except Exception as e:
            logger.error(f"Error recording usage: {str(e)}")
            return {
                "success": False,
                "message": f"Error recording usage: {str(e)}"
            }
    
    def _check_sufficient_balance(self, company_id, usage_type, quantity):
        """Check if company has sufficient balance for the requested operation"""
        
        # Test accounts always have sufficient balance
        if company_id == "test-company-id" or self.test_account:
            logger.info(f"Test account detected - bypassing balance check for {usage_type}")
            return True
            
        # Check if operation is covered by plan
        if self._is_covered_by_plan(company_id, None, usage_type, quantity):
            logger.info(f"Operation {usage_type} covered by plan for company {company_id}")
            return True
        
        # If not covered by plan, check balance
        try:
            rate = self.rates.get(usage_type, 0.10)  # Default rate if not found
            required_amount = rate * quantity
            
            balance = self._get_company_balance(company_id)
            current_balance = balance.get("balance", 0.0)
            
            # Check if balance is sufficient
            if current_balance >= required_amount:
                logger.info(f"Sufficient balance for {usage_type} - Required: ${required_amount}, Available: ${current_balance}")
                return True
            else:
                logger.warning(f"Insufficient balance for {usage_type} - Required: ${required_amount}, Available: ${current_balance}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking balance: {str(e)}")
            return False
    
    def _is_covered_by_plan(self, company_id, plan, usage_type, quantity):
        """Check if the usage is covered by the plan limits"""
        try:
            plan_details = self.plans.get(plan, {})
            
            # For free trial or testing
            if plan == "free":
                return False  # Free plan does not cover any paid features
            
            # Get current usage for this month
            current_month_start = datetime.datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            current_month_start_str = current_month_start.isoformat()
            
            db = firestore.client()
            # Get all usage for this company
            usage_docs = db.collection("usage").where("company_id", "==", company_id).get()
            
            # Filter in Python to avoid needing a composite index
            current_usage = 0
            for doc in usage_docs:
                doc_data = doc.to_dict()
                if (doc_data.get("type") == usage_type and 
                    doc_data.get("timestamp", "") >= current_month_start_str):
                    current_usage += doc_data.get("quantity", 0)
            
            # Check if this usage exceeds plan limits
            if usage_type == "post":
                if plan_details.get("monthly_posts") == "Unlimited":
                    return True
                return current_usage + quantity <= plan_details.get("monthly_posts", 0)
            
            elif usage_type == "image_generation":
                if plan_details.get("image_generation") == "Unlimited":
                    return True
                return current_usage + quantity <= plan_details.get("image_generation", 0)
            
            elif usage_type == "analytics":
                if plan_details.get("analytics") == "Unlimited":
                    return True
                return current_usage + quantity <= plan_details.get("analytics", 0)
            
            elif usage_type == "scheduled_post":
                if plan_details.get("scheduled_posts") == "Unlimited":
                    return True
                return current_usage + quantity <= plan_details.get("scheduled_posts", 0)
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking plan coverage: {str(e)}")
            return False
    
    def _deduct_from_balance(self, company_id, amount):
        """Deduct amount from company balance"""
        try:
            db = firestore.client()
            balance_ref = db.collection("balances").document(company_id)
            balance = balance_ref.get()
            
            if balance:
                current_balance = balance.to_dict()
                new_balance = max(0, current_balance.get("balance", 0) - amount)
                
                balance_ref.update({
                    "balance": new_balance,
                    "last_updated": datetime.datetime.now().isoformat()
                })
                
                # Record transaction
                db.collection("transactions").add({
                    "company_id": company_id,
                    "type": "debit",
                    "amount": amount,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "description": "Usage charge"
                })
                
                return {"success": True}
            
            return {"success": False}
        except Exception as e:
            logger.error(f"Error deducting from balance: {str(e)}")
            return {"success": False}
    
    def get_subscription_plans(self):
        """Get available subscription plans"""
        return self.plans
    
    def subscribe_to_plan(self, company_id, plan_id):
        """Subscribe company to a paid plan"""
        try:
            if plan_id not in self.plans or plan_id == "free":
                return {"error": "Invalid plan selected"}
            
            # Get customer ID
            customer_id = self._get_stripe_customer(company_id)
            if not customer_id:
                return {"error": "Could not create or find Stripe customer"}
            
            # Get price amount
            price_amount = self.plans[plan_id].get("price", 0) * 100  # Convert to cents
            
            # Create product and price in Stripe if not exists
            product = self._get_or_create_plan_product(plan_id)
            
            # Create subscription
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[
                    {"price": product["default_price"]},
                ],
                metadata={
                    "company_id": company_id,
                    "plan": plan_id
                }
            )
            
            # Update company plan
            db = firestore.client()
            db.collection("companies").document(company_id).update({
                "plan": plan_id,
                "stripe_subscription_id": subscription.id,
                "subscription_status": subscription.status,
                "plan_updated_at": datetime.datetime.now().isoformat()
            })
            
            return {
                "success": True, 
                "subscription_id": subscription.id,
                "status": subscription.status
            }
            
        except Exception as e:
            logger.error(f"Error subscribing to plan: {str(e)}")
            return {"error": str(e)}
    
    def _get_or_create_plan_product(self, plan_id):
        """Get or create Stripe product for a plan"""
        try:
            plan = self.plans.get(plan_id)
            
            # Check if product exists in Stripe
            products = stripe.Product.list(
                metadata={"plan_id": plan_id}
            )
            
            if products.data:
                return products.data[0]
            
            # Create new product and price
            product = stripe.Product.create(
                name=f"AdBot {plan['name']} Plan",
                description=f"Monthly subscription to AdBot {plan['name']} plan",
                metadata={"plan_id": plan_id}
            )
            
            # Create price for the product
            price = stripe.Price.create(
                product=product.id,
                unit_amount=int(plan["price"] * 100),  # Convert to cents
                currency="usd",
                recurring={"interval": "month"}
            )
            
            # Update product with default price
            stripe.Product.modify(
                product.id,
                default_price=price.id
            )
            
            # Refresh product data
            return stripe.Product.retrieve(product.id)
            
        except Exception as e:
            logger.error(f"Error getting/creating plan product: {str(e)}")
            raise e
    
    def cancel_subscription(self, company_id):
        """Cancel a company's subscription"""
        try:
            db = firestore.client()
            company = db.collection("companies").document(company_id).get().to_dict()
            
            if not company or "stripe_subscription_id" not in company:
                return {"error": "No active subscription found"}
            
            # Cancel in Stripe
            subscription = stripe.Subscription.modify(
                company["stripe_subscription_id"],
                cancel_at_period_end=True
            )
            
            # Update company record
            db.collection("companies").document(company_id).update({
                "subscription_status": subscription.status,
                "cancellation_requested": True,
                "cancels_at": datetime.datetime.fromtimestamp(subscription.cancel_at).isoformat() if subscription.cancel_at else None
            })
            
            return {"success": True, "cancels_at": subscription.cancel_at}
            
        except Exception as e:
            logger.error(f"Error cancelling subscription: {str(e)}")
            return {"error": str(e)} 