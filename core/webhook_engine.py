import hashlib
import hmac
import json
import os
import secrets
import threading
import time
import uuid
from datetime import datetime, timezone

import requests
from filelock import FileLock

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEBHOOK_DIR = os.path.join(_PROJECT_ROOT, "data", "webhooks")
DELIVERY_LOG_DIR = os.path.join(_PROJECT_ROOT, "data", "webhook_logs")

_VALID_EVENTS = {"critical_spike", "sentiment_drop", "new_top_issue"}
_CRITICAL_SPIKE_THRESHOLD = 20.0
_SENTIMENT_DROP_THRESHOLD = 10.0


# ─── Storage helpers ──────────────────────────────────────────────────────────

def _webhook_path(user_id: str) -> str:
    safe = "".join(c for c in user_id if c.isalnum() or c in "-_")
    return os.path.join(WEBHOOK_DIR, f"{safe}.json")


def _lock_path(user_id: str) -> str:
    safe = "".join(c for c in user_id if c.isalnum() or c in "-_")
    return os.path.join(WEBHOOK_DIR, f"{safe}.lock")


# ─── Public registration API ──────────────────────────────────────────────────

def register_webhook(user_id: str, url: str, events: list) -> dict:
    if not url.startswith("https://"):
        raise ValueError("Webhook URL must start with https://")

    os.makedirs(WEBHOOK_DIR, exist_ok=True)
    secret = secrets.token_hex(32)
    now = datetime.now(timezone.utc).isoformat()
    registration = {
        "user_id": user_id,
        "url": url,
        "secret": secret,
        "events": events,
        "active": True,
        "created_at": now,
        "last_triggered": None,
    }
    lock = FileLock(_lock_path(user_id), timeout=10)
    with lock:
        with open(_webhook_path(user_id), "w", encoding="utf-8") as f:
            json.dump(registration, f, indent=2)
    return registration


def get_webhook(user_id: str):
    path = _webhook_path(user_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def delete_webhook(user_id: str) -> None:
    try:
        path = _webhook_path(user_id)
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


# ─── HMAC signing ─────────────────────────────────────────────────────────────

def _sign_payload(payload_bytes: bytes, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"), payload_bytes, hashlib.sha256
    ).hexdigest()


# ─── HTTP delivery ────────────────────────────────────────────────────────────

def _deliver_once(url: str, payload: dict, secret: str):
    """POST payload to url. Returns (success, status_code_or_None, error_or_None). Never raises."""
    try:
        payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        signature = _sign_payload(payload_bytes, secret)
        headers = {
            "Content-Type": "application/json",
            "X-FeedbackIQ-Event": str(payload.get("event", "")),
            "X-FeedbackIQ-Signature": signature,
            "X-FeedbackIQ-Version": "1.0",
        }
        resp = requests.post(url, data=payload_bytes, headers=headers, timeout=10)
        return resp.status_code < 400, resp.status_code, None
    except Exception as exc:
        return False, None, str(exc)


def _deliver_with_retry(
    delivery_id: str, user_id: str, url: str, payload: dict, secret: str
) -> None:
    """3 attempts with 2s/4s backoff. Updates delivery log file. Never raises."""
    log_path = os.path.join(DELIVERY_LOG_DIR, f"{delivery_id}.json")

    def _save(attempts: int, status: str, code, error):
        try:
            os.makedirs(DELIVERY_LOG_DIR, exist_ok=True)
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump({
                    "delivery_id": delivery_id,
                    "user_id": user_id,
                    "event": payload.get("event"),
                    "payload": payload,
                    "attempts": attempts,
                    "last_attempt": datetime.now(timezone.utc).isoformat(),
                    "status": status,
                    "response_code": code,
                    "error": error,
                }, f, indent=2)
        except Exception:
            pass

    try:
        backoffs = [2, 4]
        status_code, error = None, None
        for attempt in range(3):
            success, status_code, error = _deliver_once(url, payload, secret)
            if success:
                _save(attempt + 1, "delivered", status_code, None)
                return
            _save(
                attempt + 1,
                "pending" if attempt < 2 else "failed",
                status_code,
                error,
            )
            if attempt < 2:
                time.sleep(backoffs[attempt])
    except Exception:
        pass


# ─── Alert conditions ─────────────────────────────────────────────────────────

def check_alert_conditions(
    session_id: str, profile: dict, dashboard_data: dict, previous_dashboard_data
) -> list:
    """Evaluate three alert conditions. Returns list of triggered event dicts."""
    triggered = []
    try:
        urgency = dashboard_data.get("urgency", {})
        critical_pct = float(urgency.get("critical_pct", 0.0))
        critical_count = int(urgency.get("critical_count", 0))

        if critical_pct > _CRITICAL_SPIKE_THRESHOLD:
            triggered.append({
                "event": "critical_spike",
                "data": {
                    "critical_count": critical_count,
                    "critical_pct": critical_pct,
                    "threshold": _CRITICAL_SPIKE_THRESHOLD,
                },
            })

        if previous_dashboard_data is not None:
            current_score = float(
                dashboard_data.get("sentiment", {}).get("overall_score", 0.0)
            )
            previous_score = float(
                previous_dashboard_data.get("sentiment", {}).get("overall_score", 0.0)
            )
            drop = previous_score - current_score
            if drop > _SENTIMENT_DROP_THRESHOLD:
                triggered.append({
                    "event": "sentiment_drop",
                    "data": {
                        "current_score": current_score,
                        "previous_score": previous_score,
                        "drop": round(drop, 2),
                    },
                })

            top_issues = dashboard_data.get("top_issues", [])
            prev_top_issues = previous_dashboard_data.get("top_issues", [])
            current_top = top_issues[0]["category"] if top_issues else None
            previous_top = prev_top_issues[0]["category"] if prev_top_issues else None
            if current_top and current_top != previous_top:
                triggered.append({
                    "event": "new_top_issue",
                    "data": {
                        "new_issue": current_top,
                        "previous_issue": previous_top,
                    },
                })
    except Exception:
        pass
    return triggered


# ─── Async dispatch ───────────────────────────────────────────────────────────

def dispatch_webhooks_async(
    user_id: str, session_id: str, profile: dict, triggered_events: list
) -> None:
    """Fire-and-forget: spawns daemon threads for each matching event. Never raises."""
    try:
        webhook = get_webhook(user_id)
        if not webhook or not webhook.get("active"):
            return

        registered_events = set(webhook.get("events", []))
        url = webhook["url"]
        wh_secret = webhook["secret"]

        for event_info in triggered_events:
            event_name = event_info.get("event", "")
            if event_name not in registered_events:
                continue

            delivery_id = str(uuid.uuid4())
            payload = {
                "version": "1.0",
                "event": event_name,
                "triggered_at": datetime.now(timezone.utc).isoformat(),
                "session_id": session_id,
                "company_name": profile.get("company_name", ""),
                "industry": profile.get("industry", ""),
                "data": event_info.get("data", {}),
            }
            t = threading.Thread(
                target=_deliver_with_retry,
                args=(delivery_id, user_id, url, payload, wh_secret),
                daemon=True,
            )
            t.start()
    except Exception:
        pass
