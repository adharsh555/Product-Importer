from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime

class ProductBase(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    active: bool = True

class ProductCreate(ProductBase):
    pass

class ProductUpdate(ProductBase):
    pass

class Product(ProductBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class WebhookBase(BaseModel):
    url: str
    event_type: str
    enabled: bool = True

class WebhookCreate(WebhookBase):
    pass

class Webhook(WebhookBase):
    id: int
    secret_key: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ImportJobBase(BaseModel):
    filename: str

class ImportJob(ImportJobBase):
    id: int
    job_id: str
    total_records: int
    processed_records: int
    status: str
    errors: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class BulkDeleteResponse(BaseModel):
    deleted_count: int
    message: str
    
    class Config:
        from_attributes = True