from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from database.db import Base

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    base_cost = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    category = Column(String)
    ml_category_id = Column(String)
    
    # Shopify
    shopify_product_id = Column(String)
    shopify_variant_id = Column(String)
    
    # Mercado Libre
    ml_item_id = Column(String, unique=True, index=True)
    ml_permalink = Column(String)
    
    # Pricing
    calculated_price = Column(Float)
    final_price = Column(Float)
    margin_percentage = Column(Float)
    
    # Costs
    ml_commission_percentage = Column(Float)
    ml_commission_amount = Column(Float)
    shipping_cost = Column(Float, default=0)
    
    # Status
    status = Column(String, default="pending")  # pending, needs_approval, approved, published, paused, killed
    score = Column(Integer, default=0)
    auto_approved = Column(Boolean, default=False)
    
    # Images
    images = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)
    
    # Relationships
    listings = relationship("Listing", back_populates="product", cascade="all, delete-orphan")
    metrics = relationship("ProductMetrics", back_populates="product", uselist=False, cascade="all, delete-orphan")
    competitor_analyses = relationship("CompetitorAnalysis", back_populates="product", cascade="all, delete-orphan")
    actions = relationship("ActionLog", back_populates="product", cascade="all, delete-orphan")


class Listing(Base):
    __tablename__ = "listings"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    # ML Data
    ml_item_id = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    listing_type_id = Column(String, default="gold_special")
    
    # Costs
    ml_commission_percentage = Column(Float)
    ml_commission_amount = Column(Float)
    shipping_cost = Column(Float, default=0)
    
    # A/B Testing
    is_ab_test = Column(Boolean, default=False)
    ab_variant = Column(String)  # A, B
    ab_test_id = Column(Integer, ForeignKey("ab_tests.id"), nullable=True)
    
    # Status
    status = Column(String, default="active")  # active, paused, ended
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    
    # Relationships
    product = relationship("Product", back_populates="listings")
    metrics = relationship("ListingMetrics", back_populates="listing", cascade="all, delete-orphan")
    ab_test = relationship("ABTest", back_populates="listings")


class ProductMetrics(Base):
    __tablename__ = "product_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), unique=True, nullable=False)
    
    # Accumulated metrics
    total_visits = Column(Integer, default=0)
    total_sales = Column(Integer, default=0)
    total_revenue = Column(Float, default=0)
    total_profit = Column(Float, default=0)
    
    # Ratios
    ctr = Column(Float, default=0)  # Click-through rate
    conversion_rate = Column(Float, default=0)
    
    # Dates
    last_sale_date = Column(DateTime, nullable=True)
    
    # Timestamps
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="metrics")


class ListingMetrics(Base):
    __tablename__ = "listing_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    
    # Daily metrics
    visits = Column(Integer, default=0)
    sales = Column(Integer, default=0)
    revenue = Column(Float, default=0)
    
    # Ads
    ad_spend = Column(Float, default=0)
    ad_impressions = Column(Integer, default=0)
    ad_clicks = Column(Integer, default=0)
    
    # Relationships
    listing = relationship("Listing", back_populates="metrics")


class CompetitorAnalysis(Base):
    __tablename__ = "competitor_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    keyword = Column(String, nullable=False)
    
    # Analysis results
    avg_price = Column(Float)
    min_price = Column(Float)
    max_price = Column(Float)
    competition_level = Column(String)  # low, medium, high
    
    # Top competitors
    top_competitors = Column(JSON)  # List of competitor items
    free_shipping_percentage = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="competitor_analyses")


class ABTest(Base):
    __tablename__ = "ab_tests"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    # Test config
    test_type = Column(String, nullable=False)  # price, title, description, combined
    variant_a_id = Column(Integer, ForeignKey("listings.id"), nullable=False)
    variant_b_id = Column(Integer, ForeignKey("listings.id"), nullable=False)
    
    # Status
    status = Column(String, default="running")  # running, completed, cancelled
    winner = Column(String, nullable=True)  # A, B, tie
    
    # Results
    results = Column(JSON)
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    

class ActionLog(Base):
    __tablename__ = "action_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    
    # Action details
    action_type = Column(String, nullable=False)  # published, paused, price_adjusted, etc
    reason = Column(String)
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    
    # Result
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="actions")
