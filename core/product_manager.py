from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from database.models import Product, ProductMetrics, ActionLog
from api.mercadolibre import ml_api
from api.shopify import shopify_api
from core.pricing_calculator import calculate_optimal_price
from core.scoring_engine import calculate_product_score
from utils.logger import logger
from datetime import datetime

class ProductManager:
    """Manage product lifecycle"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_product(self, product_data: Dict) -> Optional[Product]:
        """Create new product"""
        try:
            # Check if exists
            existing = self.db.query(Product).filter(
                Product.sku == product_data["sku"]
            ).first()
            
            if existing:
                logger.warning(f"Product already exists: {product_data['sku']}")
                return existing
            
            # Create product
            product = Product(
                sku=product_data["sku"],
                name=product_data["name"],
                base_cost=product_data["base_cost"],
                stock=product_data.get("stock", 0),
                category=product_data.get("category"),
                images=product_data.get("images", []),
                status="pending"
            )
            
            self.db.add(product)
            self.db.commit()
            self.db.refresh(product)
            
            # Create metrics
            metrics = ProductMetrics(product_id=product.id)
            self.db.add(metrics)
            self.db.commit()
            
            logger.info(f"Product created: {product.sku}")
            return product
            
        except Exception as e:
            logger.error(f"Error creating product: {str(e)}")
            self.db.rollback()
            return None
    
    def calculate_and_score(self, product_id: int) -> bool:
        """Calculate pricing and score for product"""
        try:
            product = self.db.query(Product).filter(Product.id == product_id).first()
            if not product:
                return False
            
            # Calculate pricing
            pricing = calculate_optimal_price(
                base_cost=product.base_cost,
                category_id=product.ml_category_id,
                product_name=product.name
            )
            
            if not pricing:
                logger.error(f"Failed to calculate pricing for {product.sku}")
                return False
            
            # Update product
            product.calculated_price = pricing["optimal_price"]
            product.final_price = pricing["competitive_price"]
            product.margin_percentage = pricing["margin_percentage"]
            product.ml_commission_percentage = pricing["commission_percentage"]
            product.shipping_cost = pricing["shipping_cost"]
            
            # Calculate score
            score_data = calculate_product_score(product, pricing)
            product.score = score_data["total_score"]
            
            # Determine status
            if product.score >= 80:
                product.status = "approved"
                product.auto_approved = True
            elif product.score >= 50:
                product.status = "needs_approval"
            else:
                product.status = "rejected"
            
            product.updated_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Product scored: {product.sku} = {product.score}")
            return True
            
        except Exception as e:
            logger.error(f"Error calculating and scoring: {str(e)}")
            self.db.rollback()
            return False
    
    async def publish_to_ml(self, product_id: int) -> Optional[str]:
        """Publish product to Mercado Libre"""
        try:
            product = self.db.query(Product).filter(Product.id == product_id).first()
            if not product:
                return None
            
            # Build item data
            item_data = {
                "title": product.name[:60],
                "category_id": product.ml_category_id or "MLM1055",
                "price": product.final_price,
                "currency_id": "MXN",
                "available_quantity": product.stock,
                "buying_mode": "buy_it_now",
                "listing_type_id": "gold_special",
                "condition": "new",
                "description": {
                    "plain_text": f"Producto: {product.name}\n\nSKU: {product.sku}"
                },
                "pictures": [{"source": img} for img in (product.images or [])[:10]],
                "shipping": {
                    "mode": "me2",
                    "free_shipping": product.shipping_cost == 0
                }
            }
            
            # Create item
            result = await ml_api.create_item(item_data)
            
            if result:
                product.ml_item_id = result["id"]
                product.ml_permalink = result["permalink"]
                product.status = "published"
                product.published_at = datetime.utcnow()
                self.db.commit()
                
                # Log action
                self.log_action(
                    product_id=product.id,
                    action_type="published",
                    reason=f"Auto-published with score {product.score}",
                    new_value=result["id"],
                    success=True
                )
                
                logger.info(f"Product published: {product.sku} -> {result['id']}")
                return result["id"]
            else:
                self.log_action(
                    product_id=product.id,
                    action_type="publish_failed",
                    reason="ML API error",
                    success=False
                )
                return None
                
        except Exception as e:
            logger.error(f"Error publishing to ML: {str(e)}")
            self.log_action(
                product_id=product_id,
                action_type="publish_failed",
                reason=str(e),
                success=False
            )
            return None
    
    async def sync_stock_with_shopify(self, product_id: int) -> bool:
        """Sync stock between ML and Shopify"""
        try:
            product = self.db.query(Product).filter(Product.id == product_id).first()
            if not product or not product.shopify_product_id:
                return False
            
            # Get Shopify inventory
            shopify_product = await shopify_api.get_product(product.shopify_product_id)
            if not shopify_product:
                return False
            
            shopify_stock = shopify_product["variants"][0]["inventory_quantity"]
            
            # Update if different
            if product.stock != shopify_stock:
                product.stock = shopify_stock
                self.db.commit()
                
                # Update ML if published
                if product.ml_item_id:
                    await ml_api.update_item(
                        product.ml_item_id,
                        {"available_quantity": shopify_stock}
                    )
                
                logger.info(f"Stock synced: {product.sku} = {shopify_stock}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error syncing stock: {str(e)}")
            return False
    
    def log_action(self, product_id: int, action_type: str, 
                   reason: str = None, old_value: str = None, 
                   new_value: str = None, success: bool = True,
                   error_message: str = None):
        """Log action"""
        try:
            action = ActionLog(
                product_id=product_id,
                action_type=action_type,
                reason=reason,
                old_value=old_value,
                new_value=new_value,
                success=success,
                error_message=error_message
            )
            self.db.add(action)
            self.db.commit()
        except Exception as e:
            logger.error(f"Error logging action: {str(e)}")
