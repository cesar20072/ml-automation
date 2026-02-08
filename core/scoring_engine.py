from typing import Dict
from database.models import Product
from config import business_rules
from utils.logger import logger

def calculate_product_score(product: Product, pricing_data: Dict) -> Dict:
    """
    Calculate product score (0-100)
    
    Factors:
    - Margin: 40 points (ideal ≥40%, minimum 30%)
    - Competition: 25 points (low=25, medium=15, high=5)
    - Price competitiveness: 20 points
    - Trend: 15 points (optional, from Google Trends)
    
    Returns:
        Dict with total_score and breakdown
    """
    try:
        scores = {}
        
        # 1. MARGIN SCORE (40 points)
        margin = pricing_data.get("margin_percentage", 0)
        if margin >= business_rules.IDEAL_MARGIN_PERCENTAGE:
            scores["margin"] = 40
        elif margin >= business_rules.MIN_MARGIN_PERCENTAGE:
            # Linear between 30% and 40%
            range_pct = (margin - business_rules.MIN_MARGIN_PERCENTAGE) / \
                       (business_rules.IDEAL_MARGIN_PERCENTAGE - business_rules.MIN_MARGIN_PERCENTAGE)
            scores["margin"] = int(20 + (20 * range_pct))
        else:
            scores["margin"] = 0
        
        # 2. COMPETITION SCORE (25 points)
        # TODO: Get from competitor analysis
        competition_level = "medium"  # Placeholder
        competition_scores = {
            "low": 25,
            "medium": 15,
            "high": 5
        }
        scores["competition"] = competition_scores.get(competition_level, 15)
        
        # 3. PRICE COMPETITIVENESS (20 points)
        # If price is within competitive range
        competitive_price = pricing_data.get("competitive_price", 0)
        optimal_price = pricing_data.get("optimal_price", 0)
        
        if competitive_price > 0:
            price_diff_pct = abs(competitive_price - optimal_price) / optimal_price * 100
            if price_diff_pct <= 5:
                scores["price"] = 20
            elif price_diff_pct <= 10:
                scores["price"] = 15
            elif price_diff_pct <= 15:
                scores["price"] = 10
            else:
                scores["price"] = 5
        else:
            scores["price"] = 10  # Default
        
        # 4. TREND SCORE (15 points)
        # TODO: Get from Google Trends API
        scores["trend"] = 10  # Default/placeholder
        
        # Calculate total
        total_score = sum(scores.values())
        
        return {
            "total_score": total_score,
            "breakdown": scores,
            "margin": margin,
            "competition": competition_level
        }
        
    except Exception as e:
        logger.error(f"Error calculating score: {str(e)}")
        return {
            "total_score": 0,
            "breakdown": {},
            "margin": 0,
            "competition": "unknown"
        }

def should_auto_publish(score: int) -> bool:
    """Check if product should be auto-published"""
    return score >= business_rules.SCORE_AUTO_PUBLISH

def needs_approval(score: int) -> bool:
    """Check if product needs manual approval"""
    return business_rules.SCORE_NEEDS_APPROVAL <= score < business_rules.SCORE_AUTO_PUBLISH

def should_reject(score: int) -> bool:
    """Check if product should be rejected"""
    return score < business_rules.SCORE_NEEDS_APPROVAL
