"""Producer/Consumer поверх pika с durable-очередями, DLQ и переподключением."""
from __future__ import annotations

import logging
import os
import time
from typing import Callable, Optional

import pika
from pika.exceptions import AMQPConnectionError, AMQPChannelError

logger = logging.getLogger(__name__)

QUEUE_URLS = "news_urls"
QUEUE_ARTICLES = "news_articles"
QUEUE_ERRORS = "news_errors"

ALL_QUEUES = (QUEUE_URLS, QUEUE_ARTICLES, QUEUE_ERRORS)


def _connection_params() -> pika.ConnectionParameters:
    host = os.getenv("RABBITMQ_HOST", "localhost")
    port = int(os.getenv("RABBITMQ_PORT", "5672"))
    user = os.getenv("RABBITMQ_USER", "guest")
    password = os.getenv("RABBITMQ_PASSWORD", "guest")
    credentials = pika.PlainCredentials(user, password)
    return pika.ConnectionParameters(
        host=host,
        port=port,
        credentials=credentials,
        heartbeat=60,
        blocked_connection_timeout=30,
    )


def _declare_all(channel: pika.adapters.blocking_connection.BlockingChannel) -> None:
    for name in ALL_QUEUES:
        channel.queue_declare(queue=name, durable=True)


class QueuePublisher:
    """Подключается по требованию, публикует persistent-сообщения."""

    def __init__(self) -> None:
        self._conn: Optional[pika.BlockingConnection] = None
        self._channel = None

    def _ensure(self):
        if self._conn is None or self._conn.is_closed:
            self._conn = pika.BlockingConnection(_connection_params())
            self._channel = self._conn.channel()
            _declare_all(self._channel)

    def publish(self, queue: str, body: str) -> None:
        self._ensure()
        self._channel.basic_publish(
            exchange="",
            routing_key=queue,
            body=body.encode("utf-8"),
            properties=pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent),
        )
        logger.debug("Published %d bytes to %s", len(body), queue)

    def close(self) -> None:
        if self._conn and self._conn.is_open:
            self._conn.close()
        self._conn = None
        self._channel = None

    def queue_stats(self) -> dict[str, int]:
        self._ensure()
        stats: dict[str, int] = {}
        for q in ALL_QUEUES:
            resp = self._channel.queue_declare(queue=q, durable=True, passive=True)
            stats[q] = resp.method.message_count
        return stats


class QueueConsumer:
    """Blocking consumer с автопереподключением и prefetch=1."""

    def __init__(self, queue: str, callback: Callable[[bytes], None]) -> None:
        self.queue = queue
        self.callback = callback

    def run(self) -> None:
        while True:
            try:
                conn = pika.BlockingConnection(_connection_params())
                channel = conn.channel()
                _declare_all(channel)
                channel.basic_qos(prefetch_count=1)

                def _on_message(ch, method, properties, body):
                    try:
                        self.callback(body)
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                    except Exception:
                        logger.exception("Processing failed, NACK without requeue")
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

                channel.basic_consume(queue=self.queue, on_message_callback=_on_message)
                logger.info("Consuming from %s. Ctrl+C to stop.", self.queue)
                channel.start_consuming()

            except KeyboardInterrupt:
                logger.info("Interrupted, stopping consumer.")
                try:
                    conn.close()
                except Exception:
                    pass
                return
            except (AMQPConnectionError, AMQPChannelError) as exc:
                logger.warning("AMQP error: %s. Reconnecting in 5s.", exc)
                time.sleep(5)
