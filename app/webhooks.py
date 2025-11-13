# ...existing code...
import httpx
import asyncio
from sqlalchemy.orm import Session
from app.models import Webhook
from app.config import settings
from app.database import SessionLocal


async def send_webhook_notification(event_type: str, payload: dict):
    """
    Send webhook notifications for all enabled webhooks
    subscribed to the given event_type.
    """
    session = SessionLocal()
    try:
        # Fetch all active webhooks for this event type
        webhooks = (
            session.query(Webhook)
            .filter(
                Webhook.event_type == event_type,
                Webhook.enabled == True
            )
            .all()
        )

        if not webhooks:
            return  # No webhooks to trigger

        # Create async tasks for parallel webhook delivery
        tasks = []
        for wh in webhooks:
            tasks.append(
                trigger_webhook(
                    url=wh.url,
                    payload=payload,
                    secret_key=getattr(wh, "secret_key", None)
                )
            )

        # Run all webhooks concurrently (non-blocking)
        await asyncio.gather(*tasks, return_exceptions=True)

    finally:
        session.close()


async def trigger_webhook(url: str, payload: dict, secret_key: str = None):
    """
    Trigger a single webhook endpoint.
    Supports optional secret signature header.
    """
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "ProductImporter/1.0"
    }

    if secret_key:
        headers["X-Webhook-Secret"] = secret_key

    async with httpx.AsyncClient(timeout=settings.WEBHOOK_TIMEOUT) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            return {
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "success": response.status_code < 400
            }
        except Exception as e:
            return {
                "error": str(e),
                "success": False
            }

# ...existing code...
