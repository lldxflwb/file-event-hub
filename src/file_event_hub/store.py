"""In-memory event store."""

from .models import Event, EventCreate


class EventStore:
    """In-memory store for file change events."""

    def __init__(self) -> None:
        self._events: list[Event] = []

    def add(self, event_create: EventCreate) -> Event:
        """Create an Event from EventCreate, append it, and return it."""
        event = Event(
            id=Event.generate_id(),
            **event_create.model_dump(),
        )
        self._events.append(event)
        return event

    def list(self, limit: int = 50, offset: int = 0) -> tuple[list[Event], int]:
        """Return events in reverse chronological order and total count."""
        total = len(self._events)
        # Slice from the end to avoid copying the full list
        start = max(total - offset - limit, 0)
        end = total - offset
        if end <= 0:
            return [], total
        return list(reversed(self._events[start:end])), total


event_store = EventStore()
