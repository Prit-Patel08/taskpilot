from __future__ import annotations

from typing import Any

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message
from aio_pika.abc import (
    AbstractRobustChannel,
    AbstractRobustConnection,
    AbstractRobustQueue,
)

from app.core.config import get_settings

APPLICATION_EVENTS_EXCHANGE = "taskpilot.events"
APPLICATION_DLX_EXCHANGE = "taskpilot.dlx"
APPLICATION_QUEUE_NAME = "application_queue"
APPLICATION_DLQ_NAME = "application_queue_dlq"
APPLICATION_CREATED_ROUTING_KEY = "application.created"
APPLICATION_FAILED_ROUTING_KEY = "application.failed"
APPLICATION_RETRY_ROUTING_KEY_PREFIX = "application.created.retry"
RESUME_QUEUE_NAME = "resume_queue"
RESUME_DLQ_NAME = "resume_queue_dlq"
RESUME_CREATED_ROUTING_KEY = "resume.created"
RESUME_PROCESS_ROUTING_KEY = "resume.process"
RESUME_FAILED_ROUTING_KEY = "resume.failed"
RESUME_RETRY_ROUTING_KEY_PREFIX = "resume.created.retry"
SCORING_QUEUE_NAME = "scoring_queue"
SCORING_DLQ_NAME = "scoring_queue_dlq"
SCORING_CALCULATE_ROUTING_KEY = "score.calculate"
SCORING_FAILED_ROUTING_KEY = "score.failed"
SCORING_RETRY_ROUTING_KEY_PREFIX = "score.calculate.retry"
APPLY_QUEUE_NAME = "apply_queue"
APPLY_DLQ_NAME = "apply_queue_dlq"
APPLY_REQUESTED_ROUTING_KEY = "apply.requested"
APPLY_FAILED_ROUTING_KEY = "apply.failed"
APPLY_RETRY_ROUTING_KEY_PREFIX = "apply.requested.retry"


def get_retry_routing_key(retry_number: int, *, prefix: str) -> str:
    return f"{prefix}.{retry_number}"


def get_retry_delay_seconds(*, base_delay_seconds: int, retry_number: int) -> int:
    return base_delay_seconds * (3 ** (retry_number - 1))


def build_retry_topology(
    *,
    prefix: str,
    max_retries: int,
    base_delay_seconds: int,
) -> list[tuple[str, int]]:
    return [
        (
            get_retry_routing_key(retry_number, prefix=prefix),
            get_retry_delay_seconds(
                base_delay_seconds=base_delay_seconds,
                retry_number=retry_number,
            ),
        )
        for retry_number in range(1, max_retries + 1)
    ]


async def connect_rabbitmq() -> AbstractRobustConnection:
    settings = get_settings()
    return await aio_pika.connect_robust(settings.rabbitmq_url)


async def create_application_channel(
    connection: AbstractRobustConnection,
) -> tuple[AbstractRobustChannel, AbstractRobustQueue, Any]:
    settings = get_settings()
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=5)

    exchange, queue, _ = await _declare_application_topology(
        channel,
        max_retries=settings.application_retry_max_retries,
        base_delay_seconds=settings.application_retry_base_delay_seconds,
    )
    return channel, queue, exchange


async def create_resume_channel(
    connection: AbstractRobustConnection,
) -> tuple[AbstractRobustChannel, AbstractRobustQueue, Any]:
    settings = get_settings()
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=5)

    exchange, queue, _ = await _declare_resume_topology(
        channel,
        max_retries=settings.application_retry_max_retries,
        base_delay_seconds=settings.application_retry_base_delay_seconds,
    )
    return channel, queue, exchange


async def create_scoring_channel(
    connection: AbstractRobustConnection,
) -> tuple[AbstractRobustChannel, AbstractRobustQueue, Any]:
    settings = get_settings()
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=5)

    exchange, queue, _ = await _declare_scoring_topology(
        channel,
        max_retries=settings.application_retry_max_retries,
        base_delay_seconds=settings.application_retry_base_delay_seconds,
    )
    return channel, queue, exchange


async def create_recovery_channel(
    connection: AbstractRobustConnection,
) -> tuple[AbstractRobustChannel, Any]:
    settings = get_settings()
    channel = await connection.channel()
    exchange, _, _ = await _declare_application_topology(
        channel,
        max_retries=settings.application_retry_max_retries,
        base_delay_seconds=settings.application_retry_base_delay_seconds,
    )
    await _declare_resume_topology(
        channel,
        max_retries=settings.application_retry_max_retries,
        base_delay_seconds=settings.application_retry_base_delay_seconds,
    )
    await _declare_scoring_topology(
        channel,
        max_retries=settings.application_retry_max_retries,
        base_delay_seconds=settings.application_retry_base_delay_seconds,
    )
    await _declare_apply_topology(
        channel,
        max_retries=settings.application_retry_max_retries,
        base_delay_seconds=settings.application_retry_base_delay_seconds,
    )
    return channel, exchange


async def _declare_application_topology(
    channel: AbstractRobustChannel,
    *,
    max_retries: int,
    base_delay_seconds: int,
) -> tuple[Any, AbstractRobustQueue, Any]:
    dlx_exchange = await channel.declare_exchange(
        APPLICATION_DLX_EXCHANGE,
        ExchangeType.DIRECT,
        durable=True,
    )

    exchange = await channel.declare_exchange(
        APPLICATION_EVENTS_EXCHANGE,
        ExchangeType.DIRECT,
        durable=True,
    )
    queue = await channel.declare_queue(
        APPLICATION_QUEUE_NAME,
        durable=True,
        arguments={
            "x-dead-letter-exchange": APPLICATION_DLX_EXCHANGE,
            "x-dead-letter-routing-key": APPLICATION_FAILED_ROUTING_KEY,
        },
    )
    dlq = await channel.declare_queue(
        APPLICATION_DLQ_NAME,
        durable=True,
    )
    await queue.bind(exchange, routing_key=APPLICATION_CREATED_ROUTING_KEY)
    await dlq.bind(dlx_exchange, routing_key=APPLICATION_FAILED_ROUTING_KEY)
    for retry_routing_key, delay_seconds in build_retry_topology(
        prefix=APPLICATION_RETRY_ROUTING_KEY_PREFIX,
        max_retries=max_retries,
        base_delay_seconds=base_delay_seconds,
    ):
        retry_queue = await channel.declare_queue(
            retry_routing_key,
            durable=True,
            arguments={
                "x-message-ttl": delay_seconds * 1000,
                "x-dead-letter-exchange": APPLICATION_EVENTS_EXCHANGE,
                "x-dead-letter-routing-key": APPLICATION_CREATED_ROUTING_KEY,
            },
        )
        await retry_queue.bind(exchange, routing_key=retry_routing_key)

    return exchange, queue, dlq


async def _declare_resume_topology(
    channel: AbstractRobustChannel,
    *,
    max_retries: int,
    base_delay_seconds: int,
) -> tuple[Any, AbstractRobustQueue, Any]:
    dlx_exchange = await channel.declare_exchange(
        APPLICATION_DLX_EXCHANGE,
        ExchangeType.DIRECT,
        durable=True,
    )

    exchange = await channel.declare_exchange(
        APPLICATION_EVENTS_EXCHANGE,
        ExchangeType.DIRECT,
        durable=True,
    )
    queue = await channel.declare_queue(
        RESUME_QUEUE_NAME,
        durable=True,
        arguments={
            "x-dead-letter-exchange": APPLICATION_DLX_EXCHANGE,
            "x-dead-letter-routing-key": RESUME_FAILED_ROUTING_KEY,
        },
    )
    dlq = await channel.declare_queue(
        RESUME_DLQ_NAME,
        durable=True,
    )
    await queue.bind(exchange, routing_key=RESUME_PROCESS_ROUTING_KEY)
    await queue.bind(exchange, routing_key=RESUME_CREATED_ROUTING_KEY)
    await dlq.bind(dlx_exchange, routing_key=RESUME_FAILED_ROUTING_KEY)
    for retry_routing_key, delay_seconds in build_retry_topology(
        prefix=RESUME_RETRY_ROUTING_KEY_PREFIX,
        max_retries=max_retries,
        base_delay_seconds=base_delay_seconds,
    ):
        retry_queue = await channel.declare_queue(
            retry_routing_key,
            durable=True,
            arguments={
                "x-message-ttl": delay_seconds * 1000,
                "x-dead-letter-exchange": APPLICATION_EVENTS_EXCHANGE,
                "x-dead-letter-routing-key": RESUME_CREATED_ROUTING_KEY,
            },
        )
        await retry_queue.bind(exchange, routing_key=retry_routing_key)

    return exchange, queue, dlq


async def _declare_scoring_topology(
    channel: AbstractRobustChannel,
    *,
    max_retries: int,
    base_delay_seconds: int,
) -> tuple[Any, AbstractRobustQueue, Any]:
    dlx_exchange = await channel.declare_exchange(
        APPLICATION_DLX_EXCHANGE,
        ExchangeType.DIRECT,
        durable=True,
    )

    exchange = await channel.declare_exchange(
        APPLICATION_EVENTS_EXCHANGE,
        ExchangeType.DIRECT,
        durable=True,
    )
    queue = await channel.declare_queue(
        SCORING_QUEUE_NAME,
        durable=True,
        arguments={
            "x-dead-letter-exchange": APPLICATION_DLX_EXCHANGE,
            "x-dead-letter-routing-key": SCORING_FAILED_ROUTING_KEY,
        },
    )
    dlq = await channel.declare_queue(
        SCORING_DLQ_NAME,
        durable=True,
    )
    await queue.bind(exchange, routing_key=SCORING_CALCULATE_ROUTING_KEY)
    await dlq.bind(dlx_exchange, routing_key=SCORING_FAILED_ROUTING_KEY)
    for retry_routing_key, delay_seconds in build_retry_topology(
        prefix=SCORING_RETRY_ROUTING_KEY_PREFIX,
        max_retries=max_retries,
        base_delay_seconds=base_delay_seconds,
    ):
        retry_queue = await channel.declare_queue(
            retry_routing_key,
            durable=True,
            arguments={
                "x-message-ttl": delay_seconds * 1000,
                "x-dead-letter-exchange": APPLICATION_EVENTS_EXCHANGE,
                "x-dead-letter-routing-key": SCORING_CALCULATE_ROUTING_KEY,
            },
        )
        await retry_queue.bind(exchange, routing_key=retry_routing_key)

    return exchange, queue, dlq


async def _declare_apply_topology(
    channel: AbstractRobustChannel,
    *,
    max_retries: int,
    base_delay_seconds: int,
) -> tuple[Any, AbstractRobustQueue, Any]:
    dlx_exchange = await channel.declare_exchange(
        APPLICATION_DLX_EXCHANGE,
        ExchangeType.DIRECT,
        durable=True,
    )

    exchange = await channel.declare_exchange(
        APPLICATION_EVENTS_EXCHANGE,
        ExchangeType.DIRECT,
        durable=True,
    )
    queue = await channel.declare_queue(
        APPLY_QUEUE_NAME,
        durable=True,
        arguments={
            "x-dead-letter-exchange": APPLICATION_DLX_EXCHANGE,
            "x-dead-letter-routing-key": APPLY_FAILED_ROUTING_KEY,
        },
    )
    dlq = await channel.declare_queue(
        APPLY_DLQ_NAME,
        durable=True,
    )
    await queue.bind(exchange, routing_key=APPLY_REQUESTED_ROUTING_KEY)
    await dlq.bind(dlx_exchange, routing_key=APPLY_FAILED_ROUTING_KEY)
    for retry_routing_key, delay_seconds in build_retry_topology(
        prefix=APPLY_RETRY_ROUTING_KEY_PREFIX,
        max_retries=max_retries,
        base_delay_seconds=base_delay_seconds,
    ):
        retry_queue = await channel.declare_queue(
            retry_routing_key,
            durable=True,
            arguments={
                "x-message-ttl": delay_seconds * 1000,
                "x-dead-letter-exchange": APPLICATION_EVENTS_EXCHANGE,
                "x-dead-letter-routing-key": APPLY_REQUESTED_ROUTING_KEY,
            },
        )
        await retry_queue.bind(exchange, routing_key=retry_routing_key)

    return exchange, queue, dlq


async def publish_with_headers(
    exchange: Any,
    *,
    routing_key: str,
    body: bytes,
    headers: dict[str, Any],
) -> None:
    message = Message(
        body=body,
        content_type="application/json",
        delivery_mode=DeliveryMode.PERSISTENT,
        headers=headers,
    )
    await exchange.publish(
        message,
        routing_key=routing_key,
        mandatory=True,
    )
