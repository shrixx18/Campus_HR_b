import json
from collections.abc import Awaitable, Callable

import aio_pika

from campushire_events.schemas import DomainEvent, EventType


class EventPublisher:
    EXCHANGE = "campushire.events"

    def __init__(self, url: str) -> None:
        self.url = url
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.RobustChannel | None = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(self.url)
        self._channel = await self._connection.channel()
        await self._channel.declare_exchange(self.EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True)

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()

    async def publish(self, event: DomainEvent) -> None:
        if not self._channel:
            raise RuntimeError("EventPublisher not connected")
        exchange = await self._channel.declare_exchange(self.EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True)
        body = event.model_dump_json().encode()
        await exchange.publish(
            aio_pika.Message(body=body, content_type="application/json", delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
            routing_key=event.event_type.value,
        )


EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventConsumer:
    EXCHANGE = "campushire.events"
    QUEUE = "campushire.notifications"

    def __init__(self, url: str) -> None:
        self.url = url
        self._handlers: dict[EventType, EventHandler] = {}

    def register(self, event_type: EventType, handler: EventHandler) -> None:
        self._handlers[event_type] = handler

    async def start(self) -> None:
        connection = await aio_pika.connect_robust(self.url)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)
        exchange = await channel.declare_exchange(self.EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True)
        queue = await channel.declare_queue(self.QUEUE, durable=True)

        for event_type in self._handlers:
            await queue.bind(exchange, routing_key=event_type.value)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    data = json.loads(message.body.decode())
                    event = DomainEvent.model_validate(data)
                    handler = self._handlers.get(event.event_type)
                    if handler:
                        await handler(event)
