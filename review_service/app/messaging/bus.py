# app/messaging/bus.py
import abc
import json
import os
import aio_pika
from pydantic import BaseModel

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

class MessageBus(abc.ABC):
    """Abstract base class for a message bus."""
    @abc.abstractmethod
    async def connect(self):
        raise NotImplementedError

    @abc.abstractmethod
    async def disconnect(self):
        raise NotImplementedError

    @abc.abstractmethod
    async def publish(self, topic: str, message: BaseModel):
        raise NotImplementedError

class RabbitMQBus(MessageBus):
    """RabbitMQ implementation of the MessageBus."""
    def __init__(self, url: str):
        self._url = url
        self._connection = None
        self._channel = None
        self._exchange = None

    async def connect(self):
        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()
        # Use a "topic" exchange, which is flexible for routing
        self._exchange = await self._channel.declare_exchange(
            "review_events", aio_pika.ExchangeType.TOPIC
        )
        print("[infrastructure] RabbitMQ bus connected.")

    async def disconnect(self):
        if self._connection:
            await self._connection.close()
        print("🚮 RabbitMQ bus disconnected.")

    async def publish(self, topic: str, message: BaseModel):
        if not self._exchange:
            raise RuntimeError("Bus is not connected.")
        
        # Use Pydantic's JSON serialization for the message body
        body = message.model_dump_json().encode()

        amqp_message = aio_pika.Message(
            body=body,
            content_type="application/json",
        )
        # Use the topic as the routing key
        await self._exchange.publish(amqp_message, routing_key=topic)
        print(f"📤 Published message to topic '{topic}'")

message_bus = RabbitMQBus(RABBITMQ_URL)

async def get_message_bus() -> MessageBus:
    return message_bus