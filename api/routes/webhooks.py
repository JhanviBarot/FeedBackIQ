from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.auth.dependencies import get_current_user
from core.webhook_engine import (
    register_webhook,
    get_webhook,
    delete_webhook,
    _deliver_once,
    _VALID_EVENTS,
)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

_ALL_EVENTS = list(_VALID_EVENTS)


class WebhookRegisterRequest(BaseModel):
    url: str
    events: List[str]


@router.post("")
async def create_webhook(
    body: WebhookRegisterRequest,
    current_user: dict = Depends(get_current_user),
):
    invalid = [e for e in body.events if e not in _VALID_EVENTS]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid event(s): {invalid}. Allowed: {_ALL_EVENTS}",
        )
    if not body.url.startswith("https://"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Webhook URL must start with https://",
        )
    try:
        reg = register_webhook(current_user["user_id"], body.url, body.events)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    return {
        "webhook_id": current_user["user_id"],
        "url": reg["url"],
        "events": reg["events"],
        "active": reg["active"],
        "created_at": reg["created_at"],
        "webhook_secret": reg["secret"],
    }


@router.get("")
async def read_webhook(
    current_user: dict = Depends(get_current_user),
):
    wh = get_webhook(current_user["user_id"])
    if wh is None:
        return {"registered": False}
    return {
        "registered": True,
        "url": wh["url"],
        "events": wh["events"],
        "active": wh["active"],
        "created_at": wh["created_at"],
        "last_triggered": wh.get("last_triggered"),
    }


@router.delete("")
async def remove_webhook(
    current_user: dict = Depends(get_current_user),
):
    delete_webhook(current_user["user_id"])
    return {"message": "Webhook deleted"}


@router.post("/test")
async def test_webhook(
    current_user: dict = Depends(get_current_user),
):
    wh = get_webhook(current_user["user_id"])
    if wh is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No webhook registered. Register one first.",
        )
    payload = {
        "version": "1.0",
        "event": "test",
        "triggered_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "session_id": "test",
        "company_name": "",
        "industry": "",
        "data": {"message": "This is a test webhook from FeedbackIQ"},
    }
    success, status_code, error = _deliver_once(wh["url"], payload, wh["secret"])
    return {"delivered": success, "status_code": status_code, "error": error}
