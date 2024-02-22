import logging
from collections.abc import AsyncIterator, Iterator

import anyio

logger = logging.getLogger(__name__)

MESSAGE = "Hello World!"


def sync_function(message: str = MESSAGE) -> str:
    return message


def sync_generator(message: str = MESSAGE) -> Iterator[str]:
    yield message


async def async_function(message: str = MESSAGE) -> str:
    await anyio.sleep(0.1)
    return message


async def async_generator(message: str = MESSAGE) -> AsyncIterator[str]:
    await anyio.sleep(0.1)
    yield message


def name_function(name: str = "World") -> str:
    return f"Hello {name}!"
