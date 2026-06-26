import json
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from filelock import FileLock
import pandas as pd

_THIS_FILE = os.path.abspath(__file__)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_THIS_FILE)))
SESSIONS_DIR = os.path.join(_PROJECT_ROOT, "sessions")
SESSION_TTL_HOURS = 48


class SessionStore:

    def __init__(self):
        os.makedirs(SESSIONS_DIR, exist_ok=True)

    def _path(self, session_id: str) -> str:
        safe = "".join(c for c in session_id if c.isalnum() or c == "-")
        return os.path.join(SESSIONS_DIR, f"{safe}.json")

    def _lock(self, session_id: str) -> FileLock:
        safe = "".join(c for c in session_id if c.isalnum() or c == "-")
        return FileLock(
            os.path.join(SESSIONS_DIR, f"{safe}.lock"), timeout=10)

    def _is_expired(self, session: dict) -> bool:
        try:
            updated = datetime.fromisoformat(session["last_updated"])
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) - updated > timedelta(
                hours=SESSION_TTL_HOURS)
        except Exception:
            return True

    def _cleanup_expired(self) -> None:
        try:
            for fname in os.listdir(SESSIONS_DIR):
                if not fname.endswith(".json"):
                    continue
                if fname.startswith("_"):
                    continue
                fpath = os.path.join(SESSIONS_DIR, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if self._is_expired(data):
                        os.remove(fpath)
                        lock = fpath.replace(".json", ".lock")
                        if os.path.exists(lock):
                            os.remove(lock)
                except Exception:
                    pass
        except Exception:
            pass

    @staticmethod
    def serialise_dashboard(dashboard_data: dict) -> dict:
        result = {}
        for key, value in dashboard_data.items():
            if key == "urgency_matrix":
                if isinstance(value, pd.DataFrame):
                    result[key] = value.to_dict("split")
                else:
                    result[key] = value
            else:
                result[key] = value
        return result

    @staticmethod
    def deserialise_dashboard(data: dict) -> dict:
        result = {}
        for key, value in data.items():
            if key == "urgency_matrix" and isinstance(value, dict):
                try:
                    result[key] = pd.DataFrame.from_dict(value, orient="split")
                except Exception:
                    result[key] = pd.DataFrame()
            else:
                result[key] = value
        return result

    def create_session(self, profile: dict,
                       user_id: Optional[str] = None) -> str:
        self._cleanup_expired()
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        session = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": now,
            "last_updated": now,
            "profile": profile,
            "preprocessing_result": None,
            "results_records": None,
            "results_columns": None,
            "dashboard_data_serialised": None,
            "action_plan": None,
            "classification_done": False,
            "failed_batches": [],
            "total_classified": 0,
            "gemini_fallback_count": 0,
        }
        with self._lock(session_id):
            with open(self._path(session_id), "w", encoding="utf-8") as f:
                json.dump(session, f, indent=2)
        return session_id

    def get_session(self, session_id: str) -> Optional[dict]:
        path = self._path(session_id)
        if not os.path.exists(path):
            return None
        try:
            with self._lock(session_id):
                with open(path, "r", encoding="utf-8") as f:
                    session = json.load(f)
            if self._is_expired(session):
                return None
            return session
        except Exception:
            return None

    def update_session(self, session_id: str, data: dict) -> bool:
        path = self._path(session_id)
        if not os.path.exists(path):
            return False
        try:
            with self._lock(session_id):
                with open(path, "r", encoding="utf-8") as f:
                    session = json.load(f)
                if self._is_expired(session):
                    return False
                session.update(data)
                session["session_id"] = session_id
                session["last_updated"] = datetime.now(timezone.utc).isoformat()
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(session, f, indent=2)
            return True
        except Exception:
            return False

    def session_exists(self, session_id: str) -> bool:
        return self.get_session(session_id) is not None

    def get_results_df(self, session: dict) -> Optional[pd.DataFrame]:
        records = session.get("results_records")
        columns = session.get("results_columns")
        if not records or not columns:
            return None
        try:
            return pd.DataFrame(records, columns=columns)
        except Exception:
            return None

    def get_dashboard_data(self, session: dict) -> Optional[dict]:
        raw = session.get("dashboard_data_serialised")
        if not raw:
            return None
        return self.deserialise_dashboard(raw)
