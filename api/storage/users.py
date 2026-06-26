import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional
from filelock import FileLock

_THIS_FILE = os.path.abspath(__file__)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_THIS_FILE)))
USERS_DIR = os.path.join(_PROJECT_ROOT, "users")


class UserStore:

    def __init__(self):
        os.makedirs(USERS_DIR, exist_ok=True)

    # ── Path helpers ──────────────────────────────────────────────

    def _user_path(self, user_id: str) -> str:
        safe = "".join(c for c in user_id if c.isalnum() or c == "-")
        return os.path.join(USERS_DIR, f"{safe}.json")

    def _user_lock(self, user_id: str) -> FileLock:
        safe = "".join(c for c in user_id if c.isalnum() or c == "-")
        return FileLock(
            os.path.join(USERS_DIR, f"{safe}.lock"), timeout=10)

    def _index_path(self) -> str:
        return os.path.join(USERS_DIR, "_email_index.json")

    def _index_lock(self) -> FileLock:
        return FileLock(
            os.path.join(USERS_DIR, "_email_index.lock"), timeout=10)

    # ── Email index helpers ───────────────────────────────────────

    def _read_index(self) -> dict:
        path = self._index_path()
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _write_index(self, index: dict) -> None:
        with open(self._index_path(), "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)

    # ── Public methods ────────────────────────────────────────────

    def email_exists(self, email: str) -> bool:
        return email.lower().strip() in self._read_index()

    def get_user_id_by_email(self, email: str) -> Optional[str]:
        return self._read_index().get(email.lower().strip())

    def create_user(self, email: str, hashed_password: str,
                    full_name: str) -> dict:
        email = email.lower().strip()
        with self._index_lock():
            index = self._read_index()
            if email in index:
                raise ValueError(f"Email already registered: {email}")

            user_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()
            user = {
                "user_id": user_id,
                "email": email,
                "hashed_password": hashed_password,
                "full_name": full_name.strip(),
                "created_at": now,
                "last_login": None,
                "is_active": True,
                "profile": None,
                "session_history": [],
            }
            with self._user_lock(user_id):
                with open(self._user_path(user_id), "w",
                          encoding="utf-8") as f:
                    json.dump(user, f, indent=2)
            index[email] = user_id
            self._write_index(index)

        return user

    def get_user(self, user_id: str) -> Optional[dict]:
        path = self._user_path(user_id)
        if not os.path.exists(path):
            return None
        try:
            with self._user_lock(user_id):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def get_user_by_email(self, email: str) -> Optional[dict]:
        user_id = self.get_user_id_by_email(email)
        if not user_id:
            return None
        return self.get_user(user_id)

    def update_user(self, user_id: str, data: dict) -> bool:
        path = self._user_path(user_id)
        if not os.path.exists(path):
            return False
        try:
            with self._user_lock(user_id):
                with open(path, "r", encoding="utf-8") as f:
                    user = json.load(f)
                user.update(data)
                user["user_id"] = user_id
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(user, f, indent=2)
            return True
        except (json.JSONDecodeError, IOError):
            return False

    def update_profile(self, user_id: str, profile: dict) -> bool:
        return self.update_user(user_id, {"profile": profile})

    def update_last_login(self, user_id: str) -> None:
        try:
            self.update_user(user_id, {
                "last_login": datetime.now(timezone.utc).isoformat()
            })
        except Exception:
            pass

    def add_session_to_history(self, user_id: str,
                                session_summary: dict) -> bool:
        user = self.get_user(user_id)
        if not user:
            return False
        history = user.get("session_history", [])
        history.insert(0, session_summary)
        history = history[:50]
        return self.update_user(user_id, {"session_history": history})

    def change_password(self, user_id: str,
                        new_hashed_password: str) -> bool:
        return self.update_user(user_id,
               {"hashed_password": new_hashed_password})

    def get_user_public(self, user_id: str) -> Optional[dict]:
        user = self.get_user(user_id)
        if not user:
            return None
        return {k: v for k, v in user.items() if k != "hashed_password"}
