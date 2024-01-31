from contextlib import AsyncExitStack, ExitStack

import pytest

from fastapi_inject.utils import (
    _is_async_dependency,
    _resolve_dependency_async,
    _resolve_dependency_sync,
    _solve_async_generator_async_context,
    _solve_sync_generator_async_context,
    _solve_sync_generator_sync_context,
)
from tests.code.dependencies import (
    MESSAGE,
    async_function,
    async_generator,
    sync_function,
    sync_generator,
)


def test_is_async_dependency():
    assert _is_async_dependency(async_function)
    assert _is_async_dependency(async_generator)
    assert not _is_async_dependency(sync_function)
    assert not _is_async_dependency(sync_generator)


def test_solve_sync_generator_sync_context():
    with ExitStack() as stack:
        assert _solve_sync_generator_sync_context(sync_generator, stack) == MESSAGE


@pytest.mark.anyio()
async def test_solve_sync_generator_async_context():
    async with AsyncExitStack() as stack:
        assert (
            await _solve_sync_generator_async_context(sync_generator, stack) == MESSAGE
        )


@pytest.mark.anyio()
async def test_solve_async_generator_async_context():
    async with AsyncExitStack() as stack:
        assert (
            await _solve_async_generator_async_context(async_generator, stack)
            == MESSAGE
        )


def test_resolve_dependency_sync():
    error_msg = "Cannot inject async dependency into sync function"
    with ExitStack() as stack:
        assert _resolve_dependency_sync(sync_function, stack) == MESSAGE
        assert _resolve_dependency_sync(sync_generator, stack) == MESSAGE
        with pytest.raises(ValueError, match=error_msg):
            _resolve_dependency_sync(async_function, stack)
        with pytest.raises(ValueError, match=error_msg):
            _resolve_dependency_sync(async_generator, stack)


@pytest.mark.anyio()
async def test_resolve_dependency_async():
    async with AsyncExitStack() as stack:
        assert await _resolve_dependency_async(sync_function, stack) == MESSAGE
        assert await _resolve_dependency_async(sync_generator, stack) == MESSAGE
        assert await _resolve_dependency_async(async_function, stack) == MESSAGE
        assert await _resolve_dependency_async(async_generator, stack) == MESSAGE
