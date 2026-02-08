from typing import Dict, List, Optional
from api.mercadolibre import ml_api
from database.models import CompetitorAnalysis
from sqlalchemy.orm import Session
from utils.logger import logger
import statistics

class CompetitorAnalyzer:
    """Analyze competition on Mercado Libre"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def analyze_competition(self, product_id: int, 
                                 keyword: str) -> Optional[Dict]:
        """
        Analyze competition for a product
        
        Returns:
            Dict with avg_price, min_price, max_price, competition_level, 
            top_competitors, free_shipping_percentage
        """
        try:
            # Search items
            items = await ml_api.search_items(keyword, limit=20)
            
            if not items:
                logger.warning(f"No competitors found for: {keyword}")
                return None
            
            # Extract data
            prices = []
            free_shipping_count = 0
            top_competitors = []
            
            for item in items[:10]:  # Top 10
                price = item.get("price", 0)
                if price > 0:
                    prices.append(price)
                
                if item.get("shipping", {}).get("free_shipping"):
                    free_shipping_count += 1
                
                top_competitors.append({
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "price": price,
                    "sold_quantity": item.get("sold_quantity", 0),
                    "free_shipping": item.get("shipping", {}).get("free_shipping", False)
                })
            
            # Calculate statistics
            if not prices:
                return None
            
            avg_price = statistics.mean(prices)
            min_price = min(prices)
            max_price = max(prices)
            free_shipping_pct = (free_shipping_count / len(items)) * 100
            
            # Determine competition level
            # Based on number of results and price variance
            price_variance = statistics.stdev(prices) if len(prices) > 1 else 0
            variance_pct = (price_variance / avg_price) * 100 if avg_price > 0 else 0
            
            if len(items) < 10:
                competition_level = "low"
            elif len(items) < 50 and variance_pct > 20:
                competition_level = "medium"
            else:
                competition_level = "high"
            
            # Save analysis
            analysis = CompetitorAnalysis(
                product_id=product_id,
                keyword=keyword,
                avg_price=round(avg_price, 2),
                min_price=round(min_price, 2),
                max_price=round(max_price, 2),
                competition_level=competition_level,
                top_competitors=top_competitors,
                free_shipping_percentage=round(free_shipping_pct, 2)
            )
            
            self.db.add(analysis)
            self.db.commit()
            
            logger.info(f"Competition analyzed: {keyword} = {competition_level}")
            
            return {
                "avg_price": round(avg_price, 2),
                "min_price": round(min_price, 2),
                "max_price": round(max_price, 2),
                "competition_level": competition_level,
                "top_competitors": top_competitors,
                "free_shipping_percentage": round(free_shipping_pct, 2),
                "should_offer_free_shipping": free_shipping_pct > 70
            }
            
        except Exception as e:
            logger.error(f"Error analyzing competition: {str(e)}")
            return None
    
    def get_latest_analysis(self, product_id: int) -> Optional[Dict]:
        """Get most recent competition analysis"""
        try:
            analysis = self.db.query(CompetitorAnalysis).filter(
                CompetitorAnalysis.product_id == product_id
            ).order_by(CompetitorAnalysis.created_at.desc()).first()
            
            if analysis:
                return {
                    "avg_price": analysis.avg_price,
                    "min_price": analysis.min_price,
                    "max_price": analysis.max_price,
                    "competition_level": analysis.competition_level,
                    "free_shipping_percentage": analysis.free_shipping_percentage
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting analysis: {str(e)}")
            return None
