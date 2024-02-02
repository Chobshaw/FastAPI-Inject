from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from contextlib import AsyncExitStack, ExitStack, asynccontextmanager, contextmanager
from typing import TypeVar, cast

from fastapi.concurrency import contextmanager_in_threadpool
from fastapi.dependencies.utils import (
    is_async_gen_callable,
    is_coroutine_callable,
    is_gen_callable,
)
from starlette.concurrency import run_in_threadpool

T = TypeVar("T")

SyncCallable = Callable[..., T]
SyncGeneratorCallable = Callable[..., Iterator[T]]
SyncDependency = SyncCallable[T] | SyncGeneratorCallable[T]
AsyncCallable = Callable[..., Awaitable[T]]
AsyncGeneratorCallable = Callable[..., AsyncIterator[Awaitable[T]]]
AsyncDependency = AsyncCallable[T] | AsyncGeneratorCallable[T]
Dependency = SyncDependency[T] | AsyncDependency[T]


def _is_async_dependency(dependency: Dependency) -> bool:
    return is_coroutine_callable(dependency) or is_async_gen_callable(dependency)


def _solve_sync_generator_sync_context(
    gen: SyncGeneratorCallable[T], stack: ExitStack,
) -> T:
    cm = contextmanager(gen)()
    return stack.enter_context(cm)


async def _solve_sync_generator_async_context(
    gen: SyncGeneratorCallable[T], stack: AsyncExitStack,
) -> T:
    cm = contextmanager_in_threadpool(contextmanager(gen)())
    return await stack.enter_async_context(cm)  # type: ignore[arg-type]


async def _solve_async_generator_async_context(
    gen: AsyncGeneratorCallable[T], stack: AsyncExitStack,
) -> T:
    cm = asynccontextmanager(gen)()
    return await stack.enter_async_context(cm)  # type: ignore[arg-type]


def _resolve_dependency_sync(dependency: Dependency[T], exit_stack: ExitStack) -> T:
    if _is_async_dependency(dependency):
        msg = "Cannot inject async dependency into sync function"
        raise ValueError(msg)
    if is_gen_callable(dependency):
        return _solve_sync_generator_sync_context(
            gen=cast(SyncGeneratorCallable[T], dependency), stack=exit_stack,
        )
    return cast(SyncCallable[T], dependency)()


async def _resolve_dependency_async(
    dependency: Dependency[T], async_exit_stack: AsyncExitStack,
) -> T:
    if is_gen_callable(dependency):
        return await _solve_sync_generator_async_context(
            gen=cast(SyncGeneratorCallable[T], dependency), stack=async_exit_stack,
        )
    if is_async_gen_callable(dependency):
        return await _solve_async_generator_async_context(
            gen=cast(AsyncGeneratorCallable, dependency), stack=async_exit_stack,
        )
    if is_coroutine_callable(dependency):
        return await cast(Awaitable[T], dependency())
    return await run_in_threadpool(cast(SyncCallable[T], dependency))
