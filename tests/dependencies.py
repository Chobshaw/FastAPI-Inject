import asyncio
import logging
from collections.abc import AsyncIterator, Iterator

logger = logging.getLogger(__name__)

MESSAGE = "Hello World!"


def func() -> str:
    return MESSAGE


def generator() -> Iterator[str]:
    yield MESSAGE
    logger.info("Generator finished")


async def slow_func() -> str:
    await asyncio.sleep(1)
    return MESSAGE


async def slow_generator() -> AsyncIterator[str]:
    await asyncio.sleep(1)
    yield MESSAGE
    logger.info("Generator finished")
