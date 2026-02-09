from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
from database.db import get_db
from database.models import Product, ActionLog

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Templates
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@router.get("/", response_class=HTMLResponse)
def dashboard_home(request: Request, db: Session = Depends(get_db)):
    """Main dashboard - ORVIA style"""
    
    # Stats
    total_products = db.query(Product).count()
    published = db.query(Product).filter(Product.status == "published").count()
    pending = db.query(Product).filter(Product.status == "pending").count()
    needs_approval = db.query(Product).filter(Product.status == "needs_approval").count()
    
    # Recent products
    recent_products = db.query(Product).order_by(Product.created_at.desc()).limit(10).all()
    
    return templates.TemplateResponse("dashboard_home.html", {
        "request": request,
        "stats": {
            "total": total_products,
            "published": published,
            "pending": pending,
            "needs_approval": needs_approval
        },
        "recent_products": recent_products
    })

@router.get("/upload-products", response_class=HTMLResponse)
def upload_products_page(request: Request):
    """Upload products page"""
    return templates.TemplateResponse("upload_products.html", {
        "request": request
    })

@router.get("/review-products", response_class=HTMLResponse)
def review_products_page(request: Request, status: str = "needs_approval", db: Session = Depends(get_db)):
    """Review and approve products page"""
    
    query = db.query(Product)
    
    if status != "all":
        query = query.filter(Product.status == status)
    
    products = query.order_by(Product.created_at.desc()).all()
    
    return templates.TemplateResponse("review_products.html", {
        "request": request,
        "products": products,
        "filter_status": status
    })

@router.get("/product/{product_id}", response_class=HTMLResponse)
def product_detail_page(request: Request, product_id: int, db: Session = Depends(get_db)):
    """Product detail page"""
    
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "message": "Producto no encontrado"
        })
    
    return templates.TemplateResponse("product_detail.html", {
        "request": request,
        "product": product
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
