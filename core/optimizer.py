from typing import List, Dict
from sqlalchemy.orm import Session
from database.models import Product, ProductMetrics, Listing
from datetime import datetime, timedelta
from config import business_rules
from api.mercadolibre import ml_api
from utils.logger import logger
from utils.notifications import notify_optimization

class PerformanceOptimizer:
    """Optimize product performance automatically"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def optimize_all_products(self):
        """Run optimization for all published products"""
        try:
            products = self.db.query(Product).filter(
                Product.status == "published"
            ).all()
            
            for product in products:
                await self.optimize_product(product.id)
            
            logger.info(f"Optimization completed for {len(products)} products")
            
        except Exception as e:
            logger.error(f"Error in optimization: {str(e)}")
    
    async def optimize_product(self, product_id: int):
        """Optimize single product"""
        try:
            product = self.db.query(Product).filter(Product.id == product_id).first()
            if not product or product.status != "published":
                return
            
            metrics = product.metrics
            if not metrics:
                return
            
            # Check if should pause
            if self._should_pause(product, metrics):
                await self._pause_product(product, "Low performance")
                return
            
            # Check if should adjust price
            if self._should_adjust_price(product, metrics):
                await self._adjust_price(product)
            
            # Check if should activate ads
            if self._should_activate_ads(product, metrics):
                await self._activate_ads(product)
            
            # Check if should pause ads
            if self._should_pause_ads(product, metrics):
                await self._pause_ads(product)
            
            # Check if should scale
            if self._should_scale(product, metrics):
                await self._scale_product(product)
            
        except Exception as e:
            logger.error(f"Error optimizing product {product_id}: {str(e)}")
    
    def _should_pause(self, product: Product, metrics: ProductMetrics) -> bool:
        """Check if product should be paused"""
        
        # No sales in X days + low visits
        if metrics.last_sale_date:
            days_since_sale = (datetime.utcnow() - metrics.last_sale_date).days
            if days_since_sale >= business_rules.PAUSE_NO_SALES_DAYS and \
               metrics.total_visits < business_rules.PAUSE_MIN_VISITS:
                return True
        
        # Very low CTR with decent visits
        if metrics.total_visits > 100 and metrics.ctr < business_rules.PAUSE_MIN_CTR:
            return True
        
        # Margin too low
        if product.margin_percentage < business_rules.MIN_MARGIN_PERCENTAGE:
            return True
        
        return False
    
    def _should_adjust_price(self, product: Product, metrics: ProductMetrics) -> bool:
        """Check if price should be adjusted"""
        
        # Low CTR with visits
        if metrics.total_visits > 50 and metrics.ctr < 1.0:
            return True
        
        # Low conversion with visits
        if metrics.total_visits > 200 and metrics.conversion_rate < 1.0:
            return True
        
        return False
    
    def _should_activate_ads(self, product: Product, metrics: ProductMetrics) -> bool:
        """Check if ads should be activated"""
        
        # Has sales, good margin, good CTR
        if metrics.total_sales >= business_rules.ADS_MIN_SALES and \
           product.margin_percentage >= business_rules.ADS_MIN_MARGIN and \
           metrics.ctr >= business_rules.ADS_MIN_CTR:
            return True
        
        return False
    
    def _should_pause_ads(self, product: Product, metrics: ProductMetrics) -> bool:
        """Check if ads should be paused"""
        
        # Calculate ROAS from last 7 days
        # TODO: Implement ROAS calculation
        # For now, placeholder
        roas = 0
        
        if roas > 0 and roas < business_rules.ADS_MIN_ROAS:
            return True
        
        return False
    
    def _should_scale(self, product: Product, metrics: ProductMetrics) -> bool:
        """Check if product should be scaled"""
        
        # Recent performance check (last 7 days)
        # TODO: Implement 7-day metrics
        recent_sales = metrics.total_sales  # Placeholder
        
        if recent_sales >= business_rules.SCALE_MIN_SALES_7DAYS and \
           metrics.conversion_rate >= business_rules.SCALE_MIN_CONVERSION and \
           product.margin_percentage >= (business_rules.MIN_MARGIN_PERCENTAGE + 5) and \
           product.stock >= business_rules.SCALE_MIN_STOCK:
            return True
        
        return False
    
    async def _pause_product(self, product: Product, reason: str):
        """Pause product listing"""
        try:
            if product.ml_item_id:
                await ml_api.update_item(product.ml_item_id, {"status": "paused"})
            
            product.status = "paused"
            self.db.commit()
            
            notify_optimization("Product Paused", product.name, reason)
            logger.info(f"Product paused: {product.sku} - {reason}")
            
        except Exception as e:
            logger.error(f"Error pausing product: {str(e)}")
    
    async def _adjust_price(self, product: Product):
        """Adjust product price down"""
        try:
            # Reduce price by X%
            reduction_pct = business_rules.PRICE_REDUCTION_PERCENTAGE
            new_price = product.final_price * (1 - reduction_pct / 100)
            
            # Check minimum margin
            from core.pricing_calculator import calculate_margin
            new_margin = calculate_margin(
                new_price,
                product.base_cost,
                product.ml_commission_percentage,
                product.shipping_cost
            )
            
            if new_margin < business_rules.MIN_MARGIN_PERCENTAGE:
                logger.warning(f"Cannot reduce price for {product.sku} - margin too low")
                return
            
            # Update price
            if product.ml_item_id:
                await ml_api.update_item(product.ml_item_id, {"price": new_price})
            
            old_price = product.final_price
            product.final_price = new_price
            product.margin_percentage = new_margin
            self.db.commit()
            
            notify_optimization(
                "Price Adjusted",
                product.name,
                f"Price reduced from ${old_price:.2f} to ${new_price:.2f}"
            )
            logger.info(f"Price adjusted: {product.sku} ${old_price:.2f} -> ${new_price:.2f}")
            
        except Exception as e:
            logger.error(f"Error adjusting price: {str(e)}")
    
    async def _activate_ads(self, product: Product):
        """Activate ads for product"""
        try:
            # TODO: Implement ML Ads API
            logger.info(f"Ads activated for: {product.sku}")
            notify_optimization("Ads Activated", product.name, "Product qualified for advertising")
            
        except Exception as e:
            logger.error(f"Error activating ads: {str(e)}")
    
    async def _pause_ads(self, product: Product):
        """Pause ads for product"""
        try:
            # TODO: Implement ML Ads API
            logger.info(f"Ads paused for: {product.sku}")
            notify_optimization("Ads Paused", product.name, "Low ROAS detected")
            
        except Exception as e:
            logger.error(f"Error pausing ads: {str(e)}")
    
    async def _scale_product(self, product: Product):
        """Scale successful product"""
        try:
            # Increase ad budget, consider duplicating listing, etc.
            logger.info(f"Scaling product: {product.sku}")
            notify_optimization("Product Scaled", product.name, "High performance detected")
            
        except Exception as e:
            logger.error(f"Error scaling product: {str(e)}")
