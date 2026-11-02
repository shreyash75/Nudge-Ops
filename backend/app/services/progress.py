import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone

from loguru import logger

_MAX_BUFFERED_EVENTS = 500


@dataclass
class ProgressEvent:
    """A single investigation progress update streamed to subscribers."""

    investigation_id: str
    stage: str
    status: str
    message: str
    timestamp: str

    def to_payload(self) -> dict[str, str]:
        return {
            "investigation_id": self.investigation_id,
            "stage": self.stage,
            "status": self.status,
            "message": self.message,
            "timestamp": self.timestamp,
        }


@dataclass
class _Subscriber:
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    loop: asyncio.AbstractEventLoop | None = None


class ProgressBroker:
    """In-process publish/subscribe used by the native SSE progress stream.

    POST /investigate publishes from a FastAPI worker thread while SSE
    subscribers await on the main event loop. Delivery is therefore always
    scheduled with ``loop.call_soon_threadsafe``.
    """

    def __init__(self) -> None:
        self._buffers: dict[str, list[ProgressEvent]] = {}
        self._subscribers: dict[str, list[_Subscriber]] = {}

    def publish(self, investigation_id: str, stage: str, status: str, message: str) -> None:
        """Record an event and fan it out to every SSE subscriber."""

        event = ProgressEvent(
            investigation_id=investigation_id,
            stage=stage,
            status=status,
            message=message,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        buffer = self._buffers.setdefault(investigation_id, [])
        buffer.append(event)
        del buffer[:-_MAX_BUFFERED_EVENTS]

        for subscriber in self._subscribers.get(investigation_id, []):
            loop = subscriber.loop
            if loop is not None and loop.is_running():
                # Publishing happens on worker threads as well as on the loop
                # itself; call_soon_threadsafe is safe for both.
                loop.call_soon_threadsafe(subscriber.queue.put_nowait, event)
            else:
                subscriber.queue.put_nowait(event)

    def buffered_events(self, investigation_id: str) -> list[ProgressEvent]:
        return list(self._buffers.get(investigation_id, []))

    def subscribe(self, investigation_id: str) -> "_Subscription":
        """Register an SSE subscriber, replaying events buffered so far."""

        subscriber = _Subscriber()
        try:
            subscriber.loop = asyncio.get_running_loop()
        except RuntimeError:
            subscriber.loop = None

        subscribers = self._subscribers.setdefault(investigation_id, [])
        subscribers.append(subscriber)
        logger.info("SSE subscriber joined investigation {}", investigation_id)
        return _Subscription(
            investigation_id=investigation_id,
            subscriber=subscriber,
            replay=self.buffered_events(investigation_id),
            broker=self,
        )

    def unsubscribe(self, investigation_id: str, subscriber: _Subscriber) -> None:
        participants = self._subscribers.get(investigation_id)
        if participants is None:
            return
        self._subscribers[investigation_id] = [
            existing for existing in participants if existing is not subscriber
        ]
        if not self._subscribers[investigation_id]:
            del self._subscribers[investigation_id]


@dataclass
class _Subscription:
    investigation_id: str
    subscriber: _Subscriber
    replay: list[ProgressEvent]
    broker: ProgressBroker

    def __aiter__(self):
        return self

    async def __anext__(self) -> ProgressEvent:
        if self.replay:
            return self.replay.pop(0)

        try:
            return await self.subscriber.queue.get()
        except asyncio.CancelledError as exc:
            raise StopAsyncIteration from exc


@dataclass
class InvestigationProgressPublisher:
    """Adapter used by POST /investigate to send progress to SSE subscribers."""

    investigation_id: str

    def publish(self, stage: str, status: str, message: str) -> None:
        broker.publish(self.investigation_id, stage, status, message)

    def close(self) -> None:
        return None


broker = ProgressBroker()
