from typing import Dict, Optional
from sqlalchemy.orm import Session
from database.models import ABTest, Listing, Product
from datetime import datetime, timedelta
from config import business_rules
from utils.logger import logger
from utils.notifications import notify_ab_test_completed

class ABTestManager:
    """Manage A/B tests for listings"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_test(self, product_id: int, test_type: str,
                   variant_a_data: Dict, variant_b_data: Dict) -> Optional[ABTest]:
        """
        Create new A/B test
        
        test_type: price, title, description, combined
        """
        try:
            product = self.db.query(Product).filter(Product.id == product_id).first()
            if not product:
                return None
            
            # Create variant A
            listing_a = Listing(
                product_id=product_id,
                ml_item_id=variant_a_data["ml_item_id"],
                title=variant_a_data["title"],
                description=variant_a_data.get("description"),
                price=variant_a_data["price"],
                is_ab_test=True,
                ab_variant="A",
                status="active"
            )
            self.db.add(listing_a)
            self.db.flush()
            
            # Create variant B
            listing_b = Listing(
                product_id=product_id,
                ml_item_id=variant_b_data["ml_item_id"],
                title=variant_b_data["title"],
                description=variant_b_data.get("description"),
                price=variant_b_data["price"],
                is_ab_test=True,
                ab_variant="B",
                status="active"
            )
            self.db.add(listing_b)
            self.db.flush()
            
            # Create test
            test = ABTest(
                product_id=product_id,
                test_type=test_type,
                variant_a_id=listing_a.id,
                variant_b_id=listing_b.id,
                status="running"
            )
            self.db.add(test)
            self.db.commit()
            
            logger.info(f"A/B test created: {test_type} for product {product_id}")
            return test
            
        except Exception as e:
            logger.error(f"Error creating A/B test: {str(e)}")
            self.db.rollback()
            return None
    
    def evaluate_test(self, test_id: int) -> Optional[str]:
        """
        Evaluate A/B test and determine winner
        
        Returns:
            Winner variant: "A", "B", or "tie"
        """
        try:
            test = self.db.query(ABTest).filter(ABTest.id == test_id).first()
            if not test or test.status != "running":
                return None
            
            # Check if enough time has passed
            duration = datetime.utcnow() - test.started_at
            if duration < timedelta(days=business_rules.AB_TEST_DURATION_DAYS):
                logger.info(f"Test {test_id} not ready yet")
                return None
            
            # Get listings
            listing_a = self.db.query(Listing).filter(Listing.id == test.variant_a_id).first()
            listing_b = self.db.query(Listing).filter(Listing.id == test.variant_b_id).first()
            
            if not listing_a or not listing_b:
                return None
            
            # Calculate metrics for each variant
            metrics_a = self._calculate_metrics(listing_a)
            metrics_b = self._calculate_metrics(listing_b)
            
            # Check minimum thresholds
            if metrics_a["visits"] < business_rules.AB_TEST_MIN_VISITS or \
               metrics_b["visits"] < business_rules.AB_TEST_MIN_VISITS:
                logger.info(f"Test {test_id} needs more visits")
                return None
            
            if metrics_a["sales"] < business_rules.AB_TEST_MIN_SALES and \
               metrics_b["sales"] < business_rules.AB_TEST_MIN_SALES:
                logger.info(f"Test {test_id} needs more sales")
                return None
            
            # Determine winner
            # Priority: 1. Conversion rate, 2. Sales, 3. Revenue
            winner = self._determine_winner(metrics_a, metrics_b)
            
            # Update test
            test.status = "completed"
            test.winner = winner
            test.ended_at = datetime.utcnow()
            test.results = {
                "variant_a": metrics_a,
                "variant_b": metrics_b,
                "winner": winner
            }
            
            # Pause losing variant
            if winner == "A":
                listing_b.status = "paused"
                listing_b.ended_at = datetime.utcnow()
            elif winner == "B":
                listing_a.status = "paused"
                listing_a.ended_at = datetime.utcnow()
            
            self.db.commit()
            
            # Notify
            product = self.db.query(Product).filter(Product.id == test.product_id).first()
            if product:
                notify_ab_test_completed(product.name, winner, test.results)
            
            logger.info(f"A/B test completed: {test_id}, winner: {winner}")
            return winner
            
        except Exception as e:
            logger.error(f"Error evaluating test: {str(e)}")
            return None
    
    def _calculate_metrics(self, listing: Listing) -> Dict:
        """Calculate metrics for a listing"""
        from database.models import ListingMetrics
        
        metrics = self.db.query(ListingMetrics).filter(
            ListingMetrics.listing_id == listing.id
        ).all()
        
        total_visits = sum(m.visits for m in metrics)
        total_sales = sum(m.sales for m in metrics)
        total_revenue = sum(m.revenue for m in metrics)
        
        conversion_rate = (total_sales / total_visits * 100) if total_visits > 0 else 0
        
        return {
            "visits": total_visits,
            "sales": total_sales,
            "revenue": total_revenue,
            "conversion_rate": round(conversion_rate, 2)
        }
    
    def _determine_winner(self, metrics_a: Dict, metrics_b: Dict) -> str:
        """Determine winner based on metrics"""
        
        # Compare conversion rates (most important)
        conv_a = metrics_a["conversion_rate"]
        conv_b = metrics_b["conversion_rate"]
        
        # Need at least 10% difference to declare winner
        if conv_a > conv_b * 1.1:
            return "A"
        elif conv_b > conv_a * 1.1:
            return "B"
        
        # If conversion rates are similar, compare sales
        if metrics_a["sales"] > metrics_b["sales"] * 1.1:
            return "A"
        elif metrics_b["sales"] > metrics_a["sales"] * 1.1:
            return "B"
        
        # If sales are similar, compare revenue
        if metrics_a["revenue"] > metrics_b["revenue"] * 1.1:
            return "A"
        elif metrics_b["revenue"] > metrics_a["revenue"] * 1.1:
            return "B"
        
        # Too close to call
        return "tie"
