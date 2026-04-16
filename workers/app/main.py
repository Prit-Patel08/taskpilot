from __future__ import annotations

import asyncio
import logging
import signal

from app.core.database import close_database
from app.consumers.sqs_consumer import SQSConsumer
from app.core.sqs_publisher import sqs_publisher
from app.observability.metrics import start_worker_metrics_server
from app.observability.tracing import init_tracing, shutdown_tracing
from app.recovery.stuck_job_recovery import StuckJobRecoveryLoop

logging.basicConfig(level=logging.INFO, format="%(message)s")


def _register_signal_handlers(stop_event: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signum, stop_event.set)
        except NotImplementedError:
            signal.signal(signum, lambda *_: stop_event.set())


async def run() -> None:
    stop_event = asyncio.Event()
    _register_signal_handlers(stop_event)

    sqs_consumer = SQSConsumer()
    recovery_loop = StuckJobRecoveryLoop()

    try:
        init_tracing()
        await sqs_publisher.start()
        await sqs_consumer.start()
        await recovery_loop.start()
        await stop_event.wait()
    finally:
        await recovery_loop.stop()
        await sqs_consumer.stop()
        await sqs_publisher.stop()
        await close_database()
        shutdown_tracing()


def main() -> None:
    start_worker_metrics_server()
    asyncio.run(run())


if __name__ == "__main__":
    main()
