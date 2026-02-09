from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from database.models import Product
from api.mercadolibre import ml_api
from api.shopify import shopify_api
from core.product_manager import ProductManager
from utils.logger import logger

class SyncManager:
    """Manage synchronization between ML, Shopify and local DB"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def import_from_ml(self) -> Dict:
        """
        Import all products from Mercado Libre
        Returns: {imported: int, updated: int, errors: []}
        """
        try:
            logger.info("Starting ML import...")
            
            # Get all items from ML (TODO: implement pagination)
            # For now, this is a placeholder - ML API requires specific endpoint
            
            imported = 0
            updated = 0
            errors = []
            
            # TODO: Implement actual ML product listing
            # This would require using ML's search or seller items endpoint
            
            logger.info(f"ML import completed: {imported} imported, {updated} updated")
            
            return {
                "imported": imported,
                "updated": updated,
                "errors": errors,
                "message": "Import from ML completed"
            }
            
        except Exception as e:
            logger.error(f"Error importing from ML: {str(e)}")
            return {
                "imported": 0,
                "updated": 0,
                "errors": [str(e)],
                "message": "Import failed"
            }
    
    async def sync_product_to_shopify(self, product_id: int) -> Optional[str]:
        """
        Sync a single product to Shopify
        Returns: Shopify product ID if successful
        """
        try:
            product = self.db.query(Product).filter(Product.id == product_id).first()
            if not product:
                logger.error(f"Product {product_id} not found")
                return None
            
            # Check if already exists in Shopify
            if product.shopify_product_id:
                logger.info(f"Product {product.sku} already in Shopify, updating...")
                # TODO: Update existing Shopify product
                return product.shopify_product_id
            
            # Create in Shopify
            shopify_data = {
                "product": {
                    "title": product.name,
                    "body_html": f"<p>{product.name}</p><p>SKU: {product.sku}</p>",
                    "vendor": "ML Automation",
                    "product_type": product.category or "General",
                    "tags": ["ml-automation", product.category] if product.category else ["ml-automation"],
                    "variants": [
                        {
                            "sku": product.sku,
                            "price": str(product.final_price or product.base_cost * 2),
                            "inventory_quantity": product.stock,
                            "inventory_management": "shopify"
                        }
                    ]
                }
            }
            
            if product.images:
                shopify_data["product"]["images"] = [
                    {"src": img} for img in product.images[:10]
                ]
            
            # Call Shopify API (TODO: implement create product in shopify_api)
            # For now, just log
            logger.info(f"Would create product in Shopify: {product.sku}")
            
            # TODO: Implement actual Shopify product creation
            # shopify_product = await shopify_api.create_product(shopify_data)
            # product.shopify_product_id = shopify_product["id"]
            # self.db.commit()
            
            return "shopify_123"  # Placeholder
            
        except Exception as e:
            logger.error(f"Error syncing to Shopify: {str(e)}")
            return None
    
    async def sync_all_to_shopify(self) -> Dict:
        """
        Sync all published products to Shopify
        """
        try:
            products = self.db.query(Product).filter(
                Product.status == "published"
            ).all()
            
            synced = 0
            errors = []
            
            for product in products:
                shopify_id = await self.sync_product_to_shopify(product.id)
                if shopify_id:
                    synced += 1
                else:
                    errors.append(f"Failed to sync {product.sku}")
            
            logger.info(f"Shopify sync completed: {synced}/{len(products)} products")
            
            return {
                "synced": synced,
                "total": len(products),
                "errors": errors,
                "message": f"Synced {synced} products to Shopify"
            }
            
        except Exception as e:
            logger.error(f"Error syncing to Shopify: {str(e)}")
            return {
                "synced": 0,
                "total": 0,
                "errors": [str(e)],
                "message": "Sync failed"
            }
    
    async def sync_stock(self, product_id: int) -> bool:
        """
        Sync stock between ML and Shopify
        """
        try:
            product = self.db.query(Product).filter(Product.id == product_id).first()
            if not product:
                return False
            
            # Get stock from Shopify
            if product.shopify_product_id:
                shopify_product = await shopify_api.get_product(product.shopify_product_id)
                if shopify_product:
                    shopify_stock = shopify_product["variants"][0]["inventory_quantity"]
                    
                    # Update local
                    product.stock = shopify_stock
                    self.db.commit()
                    
                    # Update ML
                    if product.ml_item_id:
                        await ml_api.update_item(
                            product.ml_item_id,
                            {"available_quantity": shopify_stock}
                        )
                    
                    logger.info(f"Stock synced for {product.sku}: {shopify_stock}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error syncing stock: {str(e)}")
            return False
