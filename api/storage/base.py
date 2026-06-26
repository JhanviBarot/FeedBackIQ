from abc import ABC, abstractmethod
from typing import Optional


class BaseSessionStore(ABC):

    @abstractmethod
    def create_session(self, profile: dict, user_id: Optional[str] = None) -> str:
        """Create a new session. Returns session_id (UUID4)."""

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[dict]:
        """Return full session dict or None if not found / expired."""

    @abstractmethod
    def update_session(self, session_id: str, data: dict) -> bool:
        """Merge data into existing session. Returns False if not found."""

    @abstractmethod
    def delete_session(self, session_id: str) -> None:
        """Delete session if it exists. Silent if not found."""

    @abstractmethod
    def session_exists(self, session_id: str) -> bool:
        """Return True if session exists and has not expired."""
