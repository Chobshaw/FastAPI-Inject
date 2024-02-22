from fastapi import Depends

from tests.code.dependencies import (
    async_function,
    async_generator,
    name_function,
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


def get_personalised_message_sync(
    name: str,
    message: str = Depends(name_function),
) -> str:
    return message


async def get_personalised_message_async(
    name: str,
    message: str = Depends(name_function),
) -> str:
    return message
