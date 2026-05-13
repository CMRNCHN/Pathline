from __future__ import annotations
import logging
from typing import Any, Callable, Dict, List
from .event_models import OperationalEvent

logger = logging.getLogger(__name__)

class EventBus:
    """
    Lightweight operational event bus for Pathline.
    Supports simple publish/subscribe for cross-workspace telemetry.
    """
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[OperationalEvent], None]]] = {}
        self._global_subscribers: List[Callable[[OperationalEvent], None]] = []

    def subscribe(self, event_type: str, callback: Callable[[OperationalEvent], None]):
        """Subscribe to a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def subscribe_all(self, callback: Callable[[OperationalEvent], None]):
        """Subscribe to all events emitted on the bus."""
        self._global_subscribers.append(callback)

    def unsubscribe(self, event_type: str, callback: Callable[[OperationalEvent], None]):
        """Unsubscribe from a specific event type."""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
            except ValueError:
                pass

    def publish(self, event: OperationalEvent):
        """Publish an event to all interested subscribers."""
        # Notify specific type subscribers
        for callback in self._subscribers.get(event.type, []):
            try:
                callback(event)
            except Exception:
                logger.exception(f"Error in event subscriber for {event.type}")

        # Notify global subscribers
        for callback in self._global_subscribers:
            try:
                callback(event)
            except Exception:
                logger.exception(f"Error in global event subscriber for {event.type}")

# Global singleton for the application process
bus = EventBus()
