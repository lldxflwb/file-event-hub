"""Pydantic models for file change events."""

import secrets
import time
from typing import Optional

from pydantic import BaseModel


class EventCreate(BaseModel):
    """Incoming event payload from hook publishers."""

    file_path: str
    tool: str
    timestamp: str
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    old_text: Optional[str] = None
    new_text: Optional[str] = None


class Event(EventCreate):
    """Stored event with server-generated id."""

    id: str

    @staticmethod
    def generate_id() -> str:
        return f"evt_{int(time.time())}_{secrets.token_hex(3)}"


class EventListResponse(BaseModel):
    """Response for listing events."""

    events: list[Event]
    total: int


class FileResponse(BaseModel):
    """Response for file content retrieval."""

    path: str
    content: Optional[str]
    exists: bool
