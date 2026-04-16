from __future__ import annotations

from typing import Any

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message

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
ATS_QUEUE_NAME = "ats_queue"
ATS_DLQ_NAME = "ats_queue_dlq"
ATS_ANALYZE_ROUTING_KEY = "ats.analyze"
ATS_FAILED_ROUTING_KEY = "ats.failed"
ATS_RETRY_ROUTING_KEY_PREFIX = "ats.analyze.retry"
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


class RabbitMQClient:
    def __init__(self) -> None:
        self._connection: Any | None = None
        self._channel: Any | None = None
        self._exchange: Any | None = None
        self._dlx_exchange: Any | None = None
        self._application_queue: Any | None = None
        self._application_dlq: Any | None = None
        self._application_retry_queues: list[Any] = []

    async def connect(self) -> None:
        if self._connection is not None and not self._connection.is_closed:
            return

        settings = get_settings()
        retry_topology = build_retry_topology(
            prefix=APPLICATION_RETRY_ROUTING_KEY_PREFIX,
            max_retries=settings.application_retry_max_retries,
            base_delay_seconds=settings.application_retry_base_delay_seconds,
        )
        resume_retry_topology = build_retry_topology(
            prefix=RESUME_RETRY_ROUTING_KEY_PREFIX,
            max_retries=settings.application_retry_max_retries,
            base_delay_seconds=settings.application_retry_base_delay_seconds,
        )
        ats_retry_topology = build_retry_topology(
            prefix=ATS_RETRY_ROUTING_KEY_PREFIX,
            max_retries=settings.application_retry_max_retries,
            base_delay_seconds=settings.application_retry_base_delay_seconds,
        )
        scoring_retry_topology = build_retry_topology(
            prefix=SCORING_RETRY_ROUTING_KEY_PREFIX,
            max_retries=settings.application_retry_max_retries,
            base_delay_seconds=settings.application_retry_base_delay_seconds,
        )
        apply_retry_topology = build_retry_topology(
            prefix=APPLY_RETRY_ROUTING_KEY_PREFIX,
            max_retries=settings.application_retry_max_retries,
            base_delay_seconds=settings.application_retry_base_delay_seconds,
        )
        self._connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        self._channel = await self._connection.channel(
            publisher_confirms=True,
            on_return_raises=True,
        )
        self._exchange = await self._channel.declare_exchange(
            APPLICATION_EVENTS_EXCHANGE,
            ExchangeType.DIRECT,
            durable=True,
        )
        self._dlx_exchange = await self._channel.declare_exchange(
            APPLICATION_DLX_EXCHANGE,
            ExchangeType.DIRECT,
            durable=True,
        )
        self._application_queue = await self._channel.declare_queue(
            APPLICATION_QUEUE_NAME,
            durable=True,
            arguments={
                "x-dead-letter-exchange": APPLICATION_DLX_EXCHANGE,
                "x-dead-letter-routing-key": APPLICATION_FAILED_ROUTING_KEY,
            },
        )
        self._application_dlq = await self._channel.declare_queue(
            APPLICATION_DLQ_NAME,
            durable=True,
        )
        await self._application_queue.bind(
            self._exchange,
            routing_key=APPLICATION_CREATED_ROUTING_KEY,
        )
        await self._application_dlq.bind(
            self._dlx_exchange,
            routing_key=APPLICATION_FAILED_ROUTING_KEY,
        )
        self._application_retry_queues = []
        for retry_routing_key, delay_seconds in retry_topology:
            retry_queue = await self._channel.declare_queue(
                retry_routing_key,
                durable=True,
                arguments={
                    "x-message-ttl": delay_seconds * 1000,
                    "x-dead-letter-exchange": APPLICATION_EVENTS_EXCHANGE,
                    "x-dead-letter-routing-key": APPLICATION_CREATED_ROUTING_KEY,
                },
            )
            await retry_queue.bind(
                self._exchange,
                routing_key=retry_routing_key,
            )
            self._application_retry_queues.append(retry_queue)
        await self._declare_resume_topology(resume_retry_topology)
        await self._declare_ats_topology(ats_retry_topology)
        await self._declare_scoring_topology(scoring_retry_topology)
        await self._declare_apply_topology(apply_retry_topology)

    async def _declare_resume_topology(
        self,
        retry_topology: list[tuple[str, int]],
    ) -> None:
        if self._channel is None or self._exchange is None or self._dlx_exchange is None:
            raise RuntimeError("RabbitMQ channel is not initialized")

        resume_queue = await self._channel.declare_queue(
            RESUME_QUEUE_NAME,
            durable=True,
            arguments={
                "x-dead-letter-exchange": APPLICATION_DLX_EXCHANGE,
                "x-dead-letter-routing-key": RESUME_FAILED_ROUTING_KEY,
            },
        )
        resume_dlq = await self._channel.declare_queue(
            RESUME_DLQ_NAME,
            durable=True,
        )
        await resume_queue.bind(
            self._exchange,
            routing_key=RESUME_CREATED_ROUTING_KEY,
        )
        await resume_queue.bind(
            self._exchange,
            routing_key=RESUME_PROCESS_ROUTING_KEY,
        )
        await resume_dlq.bind(
            self._dlx_exchange,
            routing_key=RESUME_FAILED_ROUTING_KEY,
        )
        for retry_routing_key, delay_seconds in retry_topology:
            retry_queue = await self._channel.declare_queue(
                retry_routing_key,
                durable=True,
                arguments={
                    "x-message-ttl": delay_seconds * 1000,
                    "x-dead-letter-exchange": APPLICATION_EVENTS_EXCHANGE,
                    "x-dead-letter-routing-key": RESUME_CREATED_ROUTING_KEY,
                },
            )
            await retry_queue.bind(
                self._exchange,
                routing_key=retry_routing_key,
            )

    async def _declare_scoring_topology(
        self,
        retry_topology: list[tuple[str, int]],
    ) -> None:
        if self._channel is None or self._exchange is None or self._dlx_exchange is None:
            raise RuntimeError("RabbitMQ channel is not initialized")

        scoring_queue = await self._channel.declare_queue(
            SCORING_QUEUE_NAME,
            durable=True,
            arguments={
                "x-dead-letter-exchange": APPLICATION_DLX_EXCHANGE,
                "x-dead-letter-routing-key": SCORING_FAILED_ROUTING_KEY,
            },
        )
        scoring_dlq = await self._channel.declare_queue(
            SCORING_DLQ_NAME,
            durable=True,
        )
        await scoring_queue.bind(
            self._exchange,
            routing_key=SCORING_CALCULATE_ROUTING_KEY,
        )
        await scoring_dlq.bind(
            self._dlx_exchange,
            routing_key=SCORING_FAILED_ROUTING_KEY,
        )
        for retry_routing_key, delay_seconds in retry_topology:
            retry_queue = await self._channel.declare_queue(
                retry_routing_key,
                durable=True,
                arguments={
                    "x-message-ttl": delay_seconds * 1000,
                    "x-dead-letter-exchange": APPLICATION_EVENTS_EXCHANGE,
                    "x-dead-letter-routing-key": SCORING_CALCULATE_ROUTING_KEY,
                },
            )
            await retry_queue.bind(
                self._exchange,
                routing_key=retry_routing_key,
            )

    async def _declare_ats_topology(
        self,
        retry_topology: list[tuple[str, int]],
    ) -> None:
        if self._channel is None or self._exchange is None or self._dlx_exchange is None:
            raise RuntimeError("RabbitMQ channel is not initialized")

        ats_queue = await self._channel.declare_queue(
            ATS_QUEUE_NAME,
            durable=True,
            arguments={
                "x-dead-letter-exchange": APPLICATION_DLX_EXCHANGE,
                "x-dead-letter-routing-key": ATS_FAILED_ROUTING_KEY,
            },
        )
        ats_dlq = await self._channel.declare_queue(
            ATS_DLQ_NAME,
            durable=True,
        )
        await ats_queue.bind(
            self._exchange,
            routing_key=ATS_ANALYZE_ROUTING_KEY,
        )
        await ats_dlq.bind(
            self._dlx_exchange,
            routing_key=ATS_FAILED_ROUTING_KEY,
        )
        for retry_routing_key, delay_seconds in retry_topology:
            retry_queue = await self._channel.declare_queue(
                retry_routing_key,
                durable=True,
                arguments={
                    "x-message-ttl": delay_seconds * 1000,
                    "x-dead-letter-exchange": APPLICATION_EVENTS_EXCHANGE,
                    "x-dead-letter-routing-key": ATS_ANALYZE_ROUTING_KEY,
                },
            )
            await retry_queue.bind(
                self._exchange,
                routing_key=retry_routing_key,
            )

    async def _declare_apply_topology(
        self,
        retry_topology: list[tuple[str, int]],
    ) -> None:
        if self._channel is None or self._exchange is None or self._dlx_exchange is None:
            raise RuntimeError("RabbitMQ channel is not initialized")

        apply_queue = await self._channel.declare_queue(
            APPLY_QUEUE_NAME,
            durable=True,
            arguments={
                "x-dead-letter-exchange": APPLICATION_DLX_EXCHANGE,
                "x-dead-letter-routing-key": APPLY_FAILED_ROUTING_KEY,
            },
        )
        apply_dlq = await self._channel.declare_queue(
            APPLY_DLQ_NAME,
            durable=True,
        )
        await apply_queue.bind(
            self._exchange,
            routing_key=APPLY_REQUESTED_ROUTING_KEY,
        )
        await apply_dlq.bind(
            self._dlx_exchange,
            routing_key=APPLY_FAILED_ROUTING_KEY,
        )
        for retry_routing_key, delay_seconds in retry_topology:
            retry_queue = await self._channel.declare_queue(
                retry_routing_key,
                durable=True,
                arguments={
                    "x-message-ttl": delay_seconds * 1000,
                    "x-dead-letter-exchange": APPLICATION_EVENTS_EXCHANGE,
                    "x-dead-letter-routing-key": APPLY_REQUESTED_ROUTING_KEY,
                },
            )
            await retry_queue.bind(
                self._exchange,
                routing_key=retry_routing_key,
            )

    async def close(self) -> None:
        if self._channel is not None and not self._channel.is_closed:
            await self._channel.close()

        if self._connection is not None and not self._connection.is_closed:
            await self._connection.close()

        self._application_dlq = None
        self._application_queue = None
        self._application_retry_queues = []
        self._dlx_exchange = None
        self._exchange = None
        self._channel = None
        self._connection = None

    async def publish(
        self,
        *,
        routing_key: str,
        body: bytes,
        headers: dict[str, Any] | None = None,
    ) -> None:
        if self._exchange is None:
            raise RuntimeError("RabbitMQ exchange is not initialized")

        message = Message(
            body=body,
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
            headers=headers,
        )
        await self._exchange.publish(
            message,
            routing_key=routing_key,
            mandatory=True,
        )


rabbitmq_client = RabbitMQClient()
