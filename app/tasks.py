import csv
import io
import time
import logging
from celery import current_task
from sqlalchemy import func, text
from sqlalchemy.orm import sessionmaker

from app.models import Product, ImportJob
from app.config import settings
from app.celery_app import celery_app
from app.database import SessionLocal

# Logging setup
logger = logging.getLogger(__name__)

def get_db_session():
    return SessionLocal()

@celery_app.task(bind=True)
def import_products(self, file_content: str, filename: str, job_id: str):
    db = get_db_session()
    
    try:
        # Create or update import job
        import_job = db.query(ImportJob).filter(ImportJob.job_id == job_id).first()
        if not import_job:
            import_job = ImportJob(job_id=job_id, filename=filename, status="processing")
            db.add(import_job)
        else:
            import_job.status = "processing"
        
        db.commit()
        
        # Parse CSV
        file_like = io.StringIO(file_content)
        reader = csv.DictReader(file_like)
        records = list(reader)
        
        total_records = len(records)
        import_job.total_records = total_records
        db.commit()
        
        # Process records
        processed = 0
        errors = []
        
        for record in records:
            try:
                sku = record.get('sku', '').strip()
                name = record.get('name', '').strip()
                description = record.get('description', '').strip()
                
                if not sku:
                    errors.append(f"Record {processed + 1}: Missing SKU")
                    continue
                
                # Check if product exists (case-insensitive)
                existing = db.query(Product).filter(
                    func.lower(Product.sku) == sku.lower()
                ).first()
                
                if existing:
                    # Update existing
                    existing.name = name
                    existing.description = description
                else:
                    # Create new
                    new_product = Product(
                        sku=sku,
                        name=name,
                        description=description,
                        active=True
                    )
                    db.add(new_product)
                
                processed += 1
                import_job.processed_records = processed
                
                # Update progress
                if processed % 100 == 0:
                    db.commit()
                    self.update_state(
                        state='PROGRESS',
                        meta={
                            'current': processed,
                            'total': total_records,
                            'status': f'Processed {processed}/{total_records} records'
                        }
                    )
                    
            except Exception as e:
                errors.append(f"Record {processed + 1}: {str(e)}")
                continue
        
        db.commit()
        
        # Finalize job
        if errors:
            import_job.status = "completed_with_errors"
            import_job.errors = "\n".join(errors[:10])
        else:
            import_job.status = "completed"
        
        db.commit()
        
        return {
            'current': total_records,
            'total': total_records,
            'status': f'Import completed. Processed {processed} records.',
            'processed': processed,
            'errors': len(errors)
        }
        
    except Exception as e:
        logger.error(f"Import failed: {str(e)}")
        if 'import_job' in locals():
            import_job.status = "failed"
            import_job.errors = str(e)
            db.commit()
        raise e
    
    finally:
        db.close()

@celery_app.task(bind=True)
def bulk_delete_products(self):
    db = get_db_session()
    try:
        # Get total count
        total = db.query(Product).count()
        
        if total == 0:
            return 0
        
        # Delete all products (most efficient way)
        deleted_count = db.query(Product).delete()
        db.commit()
        
        logger.info(f"Bulk delete completed: {deleted_count} products deleted")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Bulk delete failed: {str(e)}")
        db.rollback()
        raise e
    finally:
        db.close()