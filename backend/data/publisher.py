"""
TradeView — Valkey pub/sub publisher.
Publishes price update events to the tradeview:price:{symbol} channel.
"""

import json
import logging
import os

import valkey

logger = logging.getLogger(__name__)

VALKEY_HOST = os.environ.get("TV_VALKEY_HOST", "milo.local")
VALKEY_PORT = int(os.environ.get("TV_VALKEY_PORT", 6380))


class ValkeyPublisher:
    def __init__(self) -> None:
        self._client = valkey.Valkey(host=VALKEY_HOST, port=VALKEY_PORT, decode_responses=True)

    def publish(self, symbol: str, data: dict) -> None:
        channel = f"tradeview:price:{symbol}"
        self._client.publish(channel, json.dumps(data))
        logger.debug(f"Published to {channel}")
