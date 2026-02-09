from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional
from database.db import get_db
from database.models import Product
from core.product_manager import ProductManager
from pydantic import BaseModel
import csv
import io

router = APIRouter(prefix="/api/products", tags=["products"])

class ProductCreate(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    base_cost: float
    shipping_cost: Optional[float] = 0
    stock: int = 0
    category: Optional[str] = None
    listing_type: Optional[str] = "gold_special"
    images: Optional[List[str]] = []

class TitleOptimizeRequest(BaseModel):
    title: str

class ProductResponse(BaseModel):
    id: int
    sku: str
    name: str
    status: str
    score: int
    final_price: Optional[float]
    margin_percentage: Optional[float]
    ml_item_id: Optional[str]
    
    class Config:
        from_attributes = True

@router.post("/", response_model=ProductResponse)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    """Create new product"""
    manager = ProductManager(db)
    
    new_product = manager.create_product(product.dict())
    if not new_product:
        raise HTTPException(status_code=400, detail="Failed to create product")
    
    # Calculate pricing and score
    manager.calculate_and_score(new_product.id)
    
    db.refresh(new_product)
    return new_product

@router.post("/optimize-title")
async def optimize_title(request: TitleOptimizeRequest, db: Session = Depends(get_db)):
    """Optimize product title for Mercado Libre"""
    manager = ProductManager(db)
    optimized = await manager.optimize_title(request.title)
    
    if not optimized:
        return {
            "optimized_title": None,
            "message": "Could not optimize title"
        }
    
    return {
        "original_title": request.title,
        "optimized_title": optimized,
        "message": "Title optimized successfully"
    }

@router.get("/", response_model=List[ProductResponse])
def list_products(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List products"""
    query = db.query(Product)
    
    if status:
        query = query.filter(Product.status == status)
    
    products = query.offset(skip).limit(limit).all()
    return products

@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get product by ID"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.post("/{product_id}/calculate")
def recalculate_product(product_id: int, db: Session = Depends(get_db)):
    """Recalculate pricing and score"""
    manager = ProductManager(db)
    success = manager.calculate_and_score(product_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to calculate")
    
    product = db.query(Product).filter(Product.id == product_id).first()
    return product

@router.post("/{product_id}/approve")
async def approve_product(product_id: int, db: Session = Depends(get_db)):
    """Manually approve product and auto-publish if score >= 80"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.status = "approved"
    db.commit()
    
    manager = ProductManager(db)
    manager.log_action(product_id, "approved", reason="Manual approval")
    
    # Auto-publish if score >= 80
    if product.score >= 80:
        ml_item_id = await manager.publish_to_ml(product_id)
        if ml_item_id:
            return {
                "message": "Product approved and published automatically",
                "product_id": product_id,
                "ml_item_id": ml_item_id,
                "auto_published": True
            }
    
    return {
        "message": "Product approved",
        "product_id": product_id,
        "auto_published": False
    }

@router.post("/{product_id}/reject")
def reject_product(product_id: int, reason: str = None, db: Session = Depends(get_db)):
    """Reject product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.status = "rejected"
    db.commit()
    
    manager = ProductManager(db)
    manager.log_action(product_id, "rejected", reason=reason)
    
    return {"message": "Product rejected", "product_id": product_id}

@router.post("/{product_id}/publish")
async def publish_product(product_id: int, db: Session = Depends(get_db)):
    """Publish product to Mercado Libre"""
    manager = ProductManager(db)
    ml_item_id = await manager.publish_to_ml(product_id)
    
    if not ml_item_id:
        raise HTTPException(status_code=400, detail="Failed to publish")
    
    return {
        "message": "Product published",
        "product_id": product_id,
        "ml_item_id": ml_item_id
    }

@router.post("/bulk-upload")
async def bulk_upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Bulk upload products from CSV"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files allowed")
    
    content = await file.read()
    csv_file = io.StringIO(content.decode('utf-8'))
    reader = csv.DictReader(csv_file)
    
    manager = ProductManager(db)
    created = 0
    errors = []
    
    for row in reader:
        try:
            product_data = {
                "sku": row["sku"],
                "name": row["name"],
                "description": row.get("description"),
                "base_cost": float(row["base_cost"]),
                "shipping_cost": float(row.get("shipping_cost", 0)),
                "stock": int(row.get("stock", 0)),
                "category": row.get("category"),
                "listing_type": row.get("listing_type", "gold_special"),
                "images": row.get("images", "").split("|") if row.get("images") else []
            }
            
            product = manager.create_product(product_data)
            if product:
                manager.calculate_and_score(product.id)
                created += 1
            
        except Exception as e:
            errors.append(f"Row {reader.line_num}: {str(e)}")
    
    return {
        "message": f"Uploaded {created} products",
        "created": created,
        "errors": errors
    }

@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Delete product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db.delete(product)
    db.commit()
    
    return {"message": "Product deleted"}
