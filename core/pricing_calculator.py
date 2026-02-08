from typing import Dict, Optional
from config import business_rules
from utils.logger import logger

def calculate_optimal_price(base_cost: float, category_id: str = None, 
                           product_name: str = None) -> Optional[Dict]:
    """
    Calculate optimal pricing with all costs included
    
    Returns:
        Dict with: optimal_price, competitive_price, margin_percentage, 
                  commission_percentage, shipping_cost, etc.
    """
    try:
        # Default commission (if can't get from API)
        commission_percentage = 13.0  # Average for most categories
        
        # Shipping (free shipping for competitive products)
        shipping_cost = 0.0  # Will be calculated based on competition
        
        # Taxes
        iva_percentage = business_rules.IVA_PERCENTAGE
        isr_percentage = business_rules.ISR_PERCENTAGE
        
        # Total cost percentage
        total_cost_percentage = commission_percentage + isr_percentage
        
        # Calculate minimum viable price (breakeven)
        min_price = base_cost / (1 - (total_cost_percentage / 100))
        
        # Calculate price with minimum margin (30%)
        min_margin_price = base_cost / (1 - ((total_cost_percentage + business_rules.MIN_MARGIN_PERCENTAGE) / 100))
        
        # Calculate price with ideal margin (40%)
        ideal_margin_price = base_cost / (1 - ((total_cost_percentage + business_rules.IDEAL_MARGIN_PERCENTAGE) / 100))
        
        # Apply IVA
        min_price_with_iva = min_price * (1 + iva_percentage / 100)
        min_margin_price_with_iva = min_margin_price * (1 + iva_percentage / 100)
        ideal_margin_price_with_iva = ideal_margin_price * (1 + iva_percentage / 100)
        
        # Competitive price (between min margin and ideal margin)
        competitive_price = (min_margin_price_with_iva + ideal_margin_price_with_iva) / 2
        
        # Calculate actual margin at competitive price
        revenue_without_iva = competitive_price / (1 + iva_percentage / 100)
        costs = (commission_percentage + isr_percentage) / 100 * revenue_without_iva + shipping_cost
        profit = revenue_without_iva - base_cost - costs
        margin_percentage = (profit / revenue_without_iva) * 100
        
        return {
            "base_cost": round(base_cost, 2),
            "commission_percentage": commission_percentage,
            "commission_amount": round(costs, 2),
            "shipping_cost": shipping_cost,
            "iva_percentage": iva_percentage,
            "isr_percentage": isr_percentage,
            "min_price": round(min_price_with_iva, 2),
            "min_margin_price": round(min_margin_price_with_iva, 2),
            "optimal_price": round(ideal_margin_price_with_iva, 2),
            "competitive_price": round(competitive_price, 2),
            "margin_percentage": round(margin_percentage, 2),
            "profit": round(profit, 2)
        }
        
    except Exception as e:
        logger.error(f"Error calculating price: {str(e)}")
        return None

def calculate_breakeven_price(base_cost: float, commission_percentage: float,
                              shipping_cost: float = 0) -> float:
    """Calculate breakeven price"""
    iva = business_rules.IVA_PERCENTAGE
    isr = business_rules.ISR_PERCENTAGE
    
    total_cost_pct = commission_percentage + isr
    price_without_iva = (base_cost + shipping_cost) / (1 - (total_cost_pct / 100))
    price_with_iva = price_without_iva * (1 + iva / 100)
    
    return round(price_with_iva, 2)

def calculate_margin(price: float, base_cost: float, 
                    commission_percentage: float, shipping_cost: float = 0) -> float:
    """Calculate profit margin percentage"""
    try:
        iva = business_rules.IVA_PERCENTAGE
        isr = business_rules.ISR_PERCENTAGE
        
        # Remove IVA
        price_without_iva = price / (1 + iva / 100)
        
        # Calculate costs
        commission = (commission_percentage / 100) * price_without_iva
        isr_amount = (isr / 100) * price_without_iva
        total_costs = base_cost + commission + isr_amount + shipping_cost
        
        # Calculate profit
        profit = price_without_iva - total_costs
        margin = (profit / price_without_iva) * 100
        
        return round(margin, 2)
        
    except Exception as e:
        logger.error(f"Error calculating margin: {str(e)}")
        return 0.0
