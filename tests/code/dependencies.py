import logging
from collections.abc import AsyncIterator, Iterator

import anyio

logger = logging.getLogger(__name__)

MESSAGE = "Hello World!"


def sync_function() -> str:
    return MESSAGE


def sync_generator() -> Iterator[str]:
    yield MESSAGE


async def async_function() -> str:
    await anyio.sleep(0.1)
    return MESSAGE


async def async_generator() -> AsyncIterator[str]:
    await anyio.sleep(0.1)
    yield MESSAGE
