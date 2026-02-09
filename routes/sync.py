from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.db import get_db
from core.sync_manager import SyncManager

router = APIRouter(prefix="/api/sync", tags=["sync"])

@router.post("/import-from-ml")
async def import_from_ml(db: Session = Depends(get_db)):
    """Import all products from Mercado Libre"""
    sync_manager = SyncManager(db)
    result = await sync_manager.import_from_ml()
    
    return result

@router.post("/sync-to-shopify")
async def sync_all_to_shopify(db: Session = Depends(get_db)):
    """Sync all published products to Shopify"""
    sync_manager = SyncManager(db)
    result = await sync_manager.sync_all_to_shopify()
    
    return result

@router.post("/sync-product/{product_id}/shopify")
async def sync_product_to_shopify(product_id: int, db: Session = Depends(get_db)):
    """Sync a single product to Shopify"""
    sync_manager = SyncManager(db)
    shopify_id = await sync_manager.sync_product_to_shopify(product_id)
    
    if not shopify_id:
        raise HTTPException(status_code=400, detail="Failed to sync to Shopify")
    
    return {
        "message": "Product synced to Shopify",
        "product_id": product_id,
        "shopify_id": shopify_id
    }

@router.post("/sync-stock/{product_id}")
async def sync_product_stock(product_id: int, db: Session = Depends(get_db)):
    """Sync stock for a product between ML and Shopify"""
    sync_manager = SyncManager(db)
    success = await sync_manager.sync_stock(product_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to sync stock")
    
    return {"message": "Stock synced successfully", "product_id": product_id}
