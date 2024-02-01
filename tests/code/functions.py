from fastapi import Depends

from tests.code.dependencies import (
    async_function,
    async_generator,
    sync_function,
    sync_generator,
)


def get_message_no_deps(message: str) -> str:
    return message


def get_message(message: str = Depends(sync_function)) -> str:
    return message


async def get_message_async(message: str = Depends(async_function)) -> str:
    return message


def get_messages_sync(
    message_1: str = Depends(sync_function),
    message_2: str = Depends(sync_generator),
) -> list[str]:
    return [message_1, message_2]


async def get_messages_mixed_deps(
    message_1: str,
    message_2: str = Depends(async_function),
    message_3: str = Depends(sync_generator),
) -> list[str]:
    return [message_1, message_2, message_3]


async def get_messages_async(
    message_1: str = Depends(sync_function),
    message_2: str = Depends(async_function),
    message_3: str = Depends(sync_generator),
    message_4: str = Depends(async_generator),
) -> list[str]:
    return [message_1, message_2, message_3, message_4]
