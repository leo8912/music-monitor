from typing import Callable, Dict, List, Any
import asyncio
import logging

logger = logging.getLogger(__name__)

class EventBus:
    """A simple asynchronous event bus."""
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable):
        """Subscribe a handler to an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed {handler.__name__} to {event_type}")

    def clear_subscribers(self, event_type: str):
        """Clear all subscribers for an event type."""
        if event_type in self._subscribers:
            self._subscribers[event_type] = []
            logger.debug(f"Cleared subscribers for {event_type}")

    async def publish(self, event_type: str, data: Any = None):
        """Publish an event to all subscribers."""
        if event_type not in self._subscribers:
            return
        
        logger.info(f"Publishing event: {event_type}")
        
        # Execute all handlers concurrently
        tasks = []
        for handler in self._subscribers[event_type]:
            # Check if handler is awaitable
            if asyncio.iscoroutinefunction(handler):
                tasks.append(handler(data))
            else:
                # Wrap synchronous handler
                try:
                    handler(data)
                except Exception as e:
                    logger.error(f"Error in synchronous handler {handler.__name__}: {e}")

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, Exception):
                    logger.error(f"Error in async handler: {res}")

# Global instance
event_bus = EventBus()
