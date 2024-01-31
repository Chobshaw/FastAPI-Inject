import asyncio
import logging
from collections.abc import AsyncIterator, Iterator

logger = logging.getLogger(__name__)

MESSAGE = "Hello World!"


def sync_function() -> str:
    return MESSAGE


def sync_generator() -> Iterator[str]:
    yield MESSAGE
    logger.info("Generator finished")


async def async_function() -> str:
    await asyncio.sleep(0.1)
    return MESSAGE


async def async_generator() -> AsyncIterator[str]:
    await asyncio.sleep(0.1)
    yield MESSAGE
    logger.info("Generator finished")
