from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from database.db import get_db
from database.models import Product, ActionLog

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
def dashboard_home(request: Request, db: Session = Depends(get_db)):
    """Main dashboard"""
    
    # Stats
    total_products = db.query(Product).count()
    published = db.query(Product).filter(Product.status == "published").count()
    pending = db.query(Product).filter(Product.status == "pending").count()
    needs_approval = db.query(Product).filter(Product.status == "needs_approval").count()
    
    # Recent products
    recent_products = db.query(Product).order_by(Product.created_at.desc()).limit(10).all()
    
    # Recent actions
    recent_actions = db.query(ActionLog).order_by(ActionLog.created_at.desc()).limit(10).all()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": {
            "total": total_products,
            "published": published,
            "pending": pending,
            "needs_approval": needs_approval
        },
        "recent_products": recent_products,
        "recent_actions": recent_actions
    })

@router.get("/products", response_class=HTMLResponse)
def dashboard_products(request: Request, status: str = None, db: Session = Depends(get_db)):
    """Products management page"""
    
    query = db.query(Product)
    if status:
        query = query.filter(Product.status == status)
    
    products = query.order_by(Product.created_at.desc()).all()
    
    return templates.TemplateResponse("products.html", {
        "request": request,
        "products": products,
        "filter_status": status
    })

@router.get("/analytics", response_class=HTMLResponse)
def dashboard_analytics(request: Request, db: Session = Depends(get_db)):
    """Analytics page"""
    
    return templates.TemplateResponse("analytics.html", {
        "request": request
    })
