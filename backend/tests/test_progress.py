import asyncio

from app.services.progress import (
    InvestigationProgressPublisher,
    ProgressBroker,
)


async def _drain(subscription, count: int) -> list:
    events = []
    for _ in range(count):
        events.append(await subscription.__anext__())
    return events


def test_publish_buffers_events_for_subscribers():
    broker = ProgressBroker()
    broker.publish("inv-1", "gather-evidence", "running", "Collecting pods")
    broker.publish("inv-1", "diagnosis", "completed", "Done")

    buffered = broker.buffered_events("inv-1")
    assert [event.stage for event in buffered] == ["gather-evidence", "diagnosis"]
    assert buffered[0].status == "running"
    assert buffered[0].investigation_id == "inv-1"
    assert buffered[0].timestamp


def test_subscribe_replays_buffered_events_then_awaits_live_events():
    broker = ProgressBroker()
    broker.publish("inv-1", "gather-evidence", "running", "first")
    broker.publish("inv-1", "collect", "running", "second")

    subscription = broker.subscribe("inv-1")
    replayed = asyncio.run(_drain(subscription, 2))
    assert [event.message for event in replayed] == ["first", "second"]


def test_live_delivery_from_worker_thread_reaches_loop():
    async def scenario():
        broker = ProgressBroker()
        subscription = broker.subscribe("inv-2")

        # Simulate POST /investigate publishing from a worker thread with no
        # running event loop (asyncio.get_running_loop would raise there).
        await asyncio.to_thread(broker.publish, "inv-2", "analyze", "running", "live")
        return await asyncio.wait_for(subscription.__anext__(), timeout=2)

    event = asyncio.run(scenario())
    assert event.stage == "analyze"
    assert event.message == "live"


def test_events_from_other_investigations_are_not_delivered():
    async def scenario():
        broker = ProgressBroker()
        subscription = broker.subscribe("inv-3")
        broker.publish("inv-other", "analyze", "running", "not for you")
        await asyncio.sleep(0.1)
        return subscription.subscriber.queue.empty()

    assert asyncio.run(scenario())


def test_unsubscribe_stops_delivery():
    broker = ProgressBroker()
    subscription = broker.subscribe("inv-4")
    broker.unsubscribe("inv-4", subscription.subscriber)

    broker.publish("inv-4", "diagnosis", "completed", "late")
    assert broker.buffered_events("inv-4")
    assert subscription.replay == []


def test_publisher_adapter_publishes_to_broker():
    import app.services.progress as progress_module

    publisher = InvestigationProgressPublisher(investigation_id="inv-pub")
    received: list = []

    async def scenario():
        subscription = progress_module.broker.subscribe("inv-pub")
        publisher.publish("collect", "running", "via adapter")
        received.append(await asyncio.wait_for(subscription.__anext__(), timeout=2))
        publisher.close()

    asyncio.run(scenario())
    assert received[0].stage == "collect"
    assert progress_module.broker.buffered_events("inv-pub")


def test_schema_payload_shapes():
    broker = ProgressBroker()

    async def scenario():
        subscription = broker.subscribe("inv-6")
        broker.publish("inv-6", "dispatch", "running", "hello")

        event = await asyncio.wait_for(subscription.__anext__(), timeout=2)
        payload = event.to_payload()
        return set(payload.keys())

    keys = asyncio.run(scenario())
    assert keys == {
        "investigation_id",
        "stage",
        "status",
        "message",
        "timestamp",
    }
