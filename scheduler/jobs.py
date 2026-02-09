from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from database.db import SessionLocal
from database.models import Product
from core.product_manager import ProductManager
from core.optimizer import PerformanceOptimizer
from core.ab_testing import ABTestManager
from api.mercadolibre import ml_api
from api.google_sheets import sheets_api
from utils.logger import logger
from utils.notifications import notify_error
import asyncio

class JobScheduler:
    """Manage scheduled jobs"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._setup_jobs()
    
    def _setup_jobs(self):
        """Setup all scheduled jobs"""
        
        # Sync stock with Shopify - every 15 minutes
        self.scheduler.add_job(
            func=self.sync_stock_job,
            trigger=IntervalTrigger(minutes=15),
            id='sync_stock',
            name='Sync stock with Shopify',
            replace_existing=True
        )
        
        # Monitor metrics - every 6 hours
        self.scheduler.add_job(
            func=self.monitor_metrics_job,
            trigger=IntervalTrigger(hours=6),
            id='monitor_metrics',
            name='Monitor product metrics',
            replace_existing=True
        )
        
        # Optimize products - daily at 3 AM
        self.scheduler.add_job(
            func=self.optimize_products_job,
            trigger=CronTrigger(hour=3, minute=0),
            id='optimize_products',
            name='Optimize products',
            replace_existing=True
        )
        
        # Evaluate A/B tests - daily at 2 AM
        self.scheduler.add_job(
            func=self.evaluate_ab_tests_job,
            trigger=CronTrigger(hour=2, minute=0),
            id='evaluate_ab_tests',
            name='Evaluate A/B tests',
            replace_existing=True
        )
        
        # Update Google Sheets - every hour
        self.scheduler.add_job(
            func=self.update_sheets_job,
            trigger=IntervalTrigger(hours=1),
            id='update_sheets',
            name='Update Google Sheets',
            replace_existing=True
        )
        
        # Publish approved products - every 30 minutes
        self.scheduler.add_job(
            func=self.publish_approved_job,
            trigger=IntervalTrigger(minutes=30),
            id='publish_approved',
            name='Publish approved products',
            replace_existing=True
        )
        
        # Refresh ML token - every 5 hours
        self.scheduler.add_job(
            func=self.refresh_ml_token_job,
            trigger=IntervalTrigger(hours=5),
            id='refresh_token',
            name='Refresh ML token',
            replace_existing=True
        )
    
    async def sync_stock_job(self):
        """Sync stock between Shopify and ML"""
        try:
            logger.info("Starting stock sync job")
            db = SessionLocal()
            
            products = db.query(Product).filter(
                Product.status == "published",
                Product.shopify_product_id.isnot(None)
            ).all()
            
            manager = ProductManager(db)
            
            for product in products:
                await manager.sync_stock_with_shopify(product.id)
            
            db.close()
            logger.info(f"Stock sync completed: {len(products)} products")
            
        except Exception as e:
            logger.error(f"Error in stock sync job: {str(e)}")
    
    async def monitor_metrics_job(self):
        """Monitor product metrics"""
        try:
            logger.info("Starting metrics monitoring")
            # TODO: Implement metrics fetching from ML API
            logger.info("Metrics monitoring completed")
            
        except Exception as e:
            logger.error(f"Error in metrics job: {str(e)}")
    
    async def optimize_products_job(self):
        """Optimize all products"""
        try:
            logger.info("Starting optimization job")
            db = SessionLocal()
            
            optimizer = PerformanceOptimizer(db)
            await optimizer.optimize_all_products()
            
            db.close()
            logger.info("Optimization job completed")
            
        except Exception as e:
            logger.error(f"Error in optimization job: {str(e)}")
    
    async def evaluate_ab_tests_job(self):
        """Evaluate running A/B tests"""
        try:
            logger.info("Starting A/B test evaluation")
            db = SessionLocal()
            
            from database.models import ABTest
            tests = db.query(ABTest).filter(ABTest.status == "running").all()
            
            manager = ABTestManager(db)
            
            for test in tests:
                manager.evaluate_test(test.id)
            
            db.close()
            logger.info(f"A/B evaluation completed: {len(tests)} tests")
            
        except Exception as e:
            logger.error(f"Error in A/B test job: {str(e)}")
    
    async def update_sheets_job(self):
        """Update Google Sheets"""
        try:
            if not sheets_api:
                return
            
            logger.info("Starting Google Sheets sync")
            db = SessionLocal()
            
            # Get products
            products = db.query(Product).all()
            product_data = [
                {
                    "sku": p.sku,
                    "name": p.name,
                    "status": p.status,
                    "score": p.score,
                    "ml_item_id": p.ml_item_id or "",
                    "price": p.final_price or 0,
                    "margin": p.margin_percentage or 0,
                    "updated_at": p.updated_at.isoformat()
                }
                for p in products
            ]
            
            # Get recent actions
            from database.models import ActionLog
            actions = db.query(ActionLog).order_by(
                ActionLog.created_at.desc()
            ).limit(100).all()
            
            action_data = [
                {
                    "created_at": a.created_at.isoformat(),
                    "product_sku": db.query(Product).filter(Product.id == a.product_id).first().sku if a.product_id else "",
                    "action_type": a.action_type,
                    "reason": a.reason or "",
                    "success": a.success
                }
                for a in actions
            ]
            
            sheets_api.sync_all(product_data, action_data)
            
            db.close()
            logger.info("Google Sheets sync completed")
            
        except Exception as e:
            logger.error(f"Error in sheets sync job: {str(e)}")
    
    async def publish_approved_job(self):
        """Publish auto-approved products"""
        try:
            logger.info("Starting auto-publish job")
            db = SessionLocal()
            
            products = db.query(Product).filter(
                Product.status == "approved",
                Product.auto_approved == True,
                Product.ml_item_id.is_(None)
            ).all()
            
            manager = ProductManager(db)
            
            for product in products:
                await manager.publish_to_ml(product.id)
            
            db.close()
            logger.info(f"Auto-publish completed: {len(products)} products")
            
        except Exception as e:
            logger.error(f"Error in auto-publish job: {str(e)}")
    
    async def refresh_ml_token_job(self):
        """Refresh Mercado Libre access token"""
        try:
            logger.info("Refreshing ML token")
            success = await ml_api.refresh_token()
            
            if not success:
                notify_error("ML Token Refresh Failed", "Check credentials")
            
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            notify_error("ML Token Refresh Error", str(e))
    
    def start(self):
        """Start the scheduler"""
        self.scheduler.start()
        logger.info("Job scheduler started")
    
    def shutdown(self):
        """Shutdown the scheduler"""
        self.scheduler.shutdown()
        logger.info("Job scheduler stopped")

# Global scheduler instance
job_scheduler = JobScheduler()
