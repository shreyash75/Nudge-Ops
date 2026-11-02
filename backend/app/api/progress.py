import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.auth import decode_access_token
from app.services.progress import broker

router = APIRouter(tags=["investigation-progress"])

_HEARTBEAT_SECONDS = 10.0
_MAX_STREAM_SECONDS = 900.0


@router.get("/investigate/progress/{investigation_id}")
async def stream_progress(
    investigation_id: str,
    token: str,
    request: Request,
) -> StreamingResponse:
    """Stream live investigation progress as Server-Sent Events.

    EventSource cannot set headers, so the FastAPI access token is accepted
    as a query parameter; it is validated before the stream starts.
    """

    decode_access_token(token)

    subscription = broker.subscribe(investigation_id)
    replay = list(subscription.replay)
    queue = subscription.subscriber.queue

    async def event_stream():
        try:
            for event in replay:
                yield f"data: {json.dumps(event.to_payload())}\n\n"

            elapsed = 0.0
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=_HEARTBEAT_SECONDS)
                    elapsed = 0.0
                except asyncio.TimeoutError:
                    elapsed += _HEARTBEAT_SECONDS
                    if elapsed >= _MAX_STREAM_SECONDS:
                        break
                    yield ": keep-alive\n\n"
                    continue

                yield f"data: {json.dumps(event.to_payload())}\n\n"

                if event.stage == "completed":
                    break
        finally:
            broker.unsubscribe(investigation_id, subscription.subscriber)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
