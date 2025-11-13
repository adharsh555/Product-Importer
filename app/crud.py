from sqlalchemy.orm import Session
from sqlalchemy import or_, func, text
from typing import List, Optional
from app.models import Product, Webhook, ImportJob
from app.schemas import ProductCreate, ProductUpdate, WebhookCreate

# Product CRUD
def get_products(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    sku: Optional[str] = None,
    name: Optional[str] = None,
    active: Optional[bool] = None,
    description: Optional[str] = None
) -> List[Product]:
    query = db.query(Product)
    
    if sku:
        query = query.filter(Product.sku.ilike(f"%{sku}%"))
    if name:
        query = query.filter(Product.name.ilike(f"%{name}%"))
    if active is not None:
        query = query.filter(Product.active == active)
    if description:
        query = query.filter(Product.description.ilike(f"%{description}%"))
    
    return query.offset(skip).limit(limit).all()

def get_product(db: Session, product_id: int) -> Optional[Product]:
    return db.query(Product).filter(Product.id == product_id).first()

def get_product_by_sku(db: Session, sku: str) -> Optional[Product]:
    return db.query(Product).filter(func.lower(Product.sku) == sku.lower()).first()

def create_product(db: Session, product: ProductCreate) -> Product:
    db_product = Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

def update_product(db: Session, product_id: int, product: ProductUpdate) -> Optional[Product]:
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if db_product:
        for key, value in product.dict().items():
            setattr(db_product, key, value)
        db.commit()
        db.refresh(db_product)
    return db_product

def delete_product(db: Session, product_id: int) -> bool:
    try:
        db_product = db.query(Product).filter(Product.id == product_id).first()
        if db_product:
            db.delete(db_product)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        print(f"Error deleting product {product_id}: {e}")
        return False

def get_products_count(db: Session) -> int:
    return db.query(Product).count()

def delete_all_products_sync(db: Session) -> int:
    """Delete all products - SIMPLE AND GUARANTEED"""
    try:
        # Method 1: Simple SQLAlchemy delete
        count_before = db.query(Product).count()
        print(f"Products before delete: {count_before}")
        
        if count_before == 0:
            return 0
            
        # This is the most reliable way
        deleted_count = db.query(Product).delete()
        db.commit()
        
        count_after = db.query(Product).count()
        print(f"Products after delete: {count_after}")
        
        return deleted_count
        
    except Exception as e:
        print(f"CRUD Delete Error: {e}")
        db.rollback()
        raise e

# Webhook CRUD
def get_webhooks(db: Session) -> List[Webhook]:
    return db.query(Webhook).all()

def create_webhook(db: Session, webhook: WebhookCreate) -> Webhook:
    db_webhook = Webhook(**webhook.dict())
    db.add(db_webhook)
    db.commit()
    db.refresh(db_webhook)
    return db_webhook

def delete_webhook(db: Session, webhook_id: int) -> bool:
    db_webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if db_webhook:
        db.delete(db_webhook)
        db.commit()
        return True
    return False

# Import Job CRUD
def create_import_job(db: Session, job_id: str, filename: str) -> ImportJob:
    db_job = ImportJob(job_id=job_id, filename=filename)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

def get_import_job(db: Session, job_id: str) -> Optional[ImportJob]:
    return db.query(ImportJob).filter(ImportJob.job_id == job_id).first()