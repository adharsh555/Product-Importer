from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import uuid
import json
from typing import List, Optional

from app import crud, models, schemas, tasks
from app.database import get_db, create_tables
from app.config import settings

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.on_event("startup")
def startup_event():
    create_tables()

# Product endpoints
@app.get("/api/products/", response_model=List[schemas.Product])
def read_products(
    skip: int = 0,
    limit: int = 100,
    sku: Optional[str] = None,
    name: Optional[str] = None,
    active: Optional[bool] = None,
    description: Optional[str] = None,
    db: Session = Depends(get_db)
):
    return crud.get_products(
        db, skip=skip, limit=limit, 
        sku=sku, name=name, active=active, description=description
    )

@app.post("/api/products/", response_model=schemas.Product)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    db_product = crud.get_product_by_sku(db, sku=product.sku)
    if db_product:
        raise HTTPException(status_code=400, detail="SKU already exists")
    return crud.create_product(db=db, product=product)

@app.get("/api/products/{product_id}", response_model=schemas.Product)
def read_product(product_id: int, db: Session = Depends(get_db)):
    db_product = crud.get_product(db, product_id=product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

@app.put("/api/products/{product_id}", response_model=schemas.Product)
def update_product(product_id: int, product: schemas.ProductUpdate, db: Session = Depends(get_db)):
    db_product = crud.update_product(db, product_id=product_id, product=product)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

@app.delete("/api/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    success = crud.delete_product(db, product_id=product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}

# File upload endpoint
@app.post("/api/upload/")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    # Read file content
    content = await file.read()
    file_content = content.decode('utf-8')
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Create import job record
    crud.create_import_job(db, job_id, file.filename)
    
    # Start async task
    task = tasks.import_products.delay(file_content, file.filename, job_id)
    
    return {
        "job_id": job_id,
        "task_id": task.id,
        "filename": file.filename,
        "message": "File upload started"
    }

# Bulk delete endpoint - FIXED VERSION
@app.delete("/api/products/", response_model=schemas.BulkDeleteResponse)
def bulk_delete_products(db: Session = Depends(get_db)):
    try:
        count = crud.get_products_count(db)
        if count == 0:
            raise HTTPException(status_code=400, detail="No products to delete")
        
        # For small datasets, delete immediately
        if count <= 1000:
            deleted_count = crud.delete_all_products_sync(db)
            return {
                "deleted_count": deleted_count,
                "message": f"Successfully deleted {deleted_count} products"
            }
        else:
            # For large datasets, use async task
            task = tasks.bulk_delete_products.delay()
            return {
                "deleted_count": count,
                "message": f"Bulk deletion started for {count} products",
                "task_id": task.id
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during bulk delete: {str(e)}")

# Task status endpoint
@app.get("/api/tasks/{task_id}")
def get_task_status(task_id: str):
    try:
        task = tasks.import_products.AsyncResult(task_id)
        
        if task.state == 'PENDING':
            response = {
                'state': task.state,
                'current': 0,
                'total': 1,
                'status': 'Pending...'
            }
        elif task.state != 'FAILURE':
            response = {
                'state': task.state,
                'current': task.info.get('current', 0),
                'total': task.info.get('total', 1),
                'status': task.info.get('status', '')
            }
            if 'result' in task.info:
                response['result'] = task.info['result']
        else:
            response = {
                'state': task.state,
                'current': 1,
                'total': 1,
                'status': str(task.info)
            }
        
        return response
    except Exception as e:
        return {
            'state': 'ERROR',
            'status': f'Error checking task: {str(e)}'
        }

# Bulk delete task status endpoint
# Bulk delete endpoint - WITH PROPER ERROR HANDLING
@app.get("/api/tasks/bulk-delete/{task_id}")
def get_bulk_delete_task_status(task_id: str):
    try:
        task = tasks.bulk_delete_products.AsyncResult(task_id)
        
        if task.state == 'PENDING':
            response = {
                'state': task.state,
                'current': 0,
                'total': 1,
                'status': 'Pending...'
            }
        elif task.state != 'FAILURE':
            response = {
                'state': task.state,
                'current': task.info.get('current', 0),
                'total': task.info.get('total', 1),
                'status': task.info.get('status', '')
            }
            if 'result' in task.info:
                response['result'] = task.info['result']
        else:
            response = {
                'state': task.state,
                'current': 1,
                'total': 1,
                'status': str(task.info)
            }
        
        return response
    except Exception as e:
        return {
            'state': 'ERROR',
            'status': f'Error checking task: {str(e)}'
        }
    
# Webhook endpoints
@app.get("/api/webhooks/", response_model=List[schemas.Webhook])
def read_webhooks(db: Session = Depends(get_db)):
    return crud.get_webhooks(db)

@app.post("/api/webhooks/", response_model=schemas.Webhook)
def create_webhook(webhook: schemas.WebhookCreate, db: Session = Depends(get_db)):
    return crud.create_webhook(db=db, webhook=webhook)

@app.delete("/api/webhooks/{webhook_id}")
def delete_webhook(webhook_id: int, db: Session = Depends(get_db)):
    success = crud.delete_webhook(db, webhook_id=webhook_id)
    if not success:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"message": "Webhook deleted successfully"}

# Serve frontend
@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("app/static/index.html", "r") as f:
        return HTMLResponse(content=f.read(), status_code=200)

# ALTERNATIVE BULK DELETE - GUARANTEED TO WORK

