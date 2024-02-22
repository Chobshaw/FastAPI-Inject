import functools
import inspect
from collections.abc import Awaitable, Callable, Iterator
from contextlib import AsyncExitStack, ExitStack
from typing import Any, NamedTuple, ParamSpec, TypeVar, cast, overload

import asyncer
from fastapi import FastAPI
from fastapi.params import Depends

from fastapi_inject.enable import _get_app_instance
from fastapi_inject.utils import (
    AsyncDependency,
    Dependency,
    SyncDependency,
    _call_dependency_async,
    _call_dependency_sync,
)

T = TypeVar("T")
P = ParamSpec("P")


class DependencyInfo(NamedTuple):
    name: str
    dependency: Dependency | None


def _get_call_kwargs(
    func: Callable[P, T],
    *args: P.args,
    **kwargs: P.kwargs,
) -> dict[str, Any]:
    call_kwargs = {}
    i = 0
    for param in inspect.signature(func).parameters.values():
        if i < len(args):
            call_kwargs[param.name] = args[i]
            i += 1
        elif param.name in kwargs:
            call_kwargs[param.name] = kwargs[param.name]
        elif isinstance(param.default, Depends):
            continue
        elif param.default != inspect.Parameter.empty:
            call_kwargs[param.name] = param.default
    return call_kwargs


def _sub_dependencies(
    dependency: Dependency,
    app_instance: FastAPI,
) -> Iterator[DependencyInfo]:
    for param in inspect.signature(dependency).parameters.values():
        if not isinstance(param.default, Depends):
            yield DependencyInfo(param.name, None)
            continue
        if param.default.dependency is None:
            error_msg = (
                "Depends instance must have a dependency. "
                "Please add a dependency or use a type annotation"
            )
            raise ValueError(error_msg)
        yield DependencyInfo(
            param.name,
            app_instance.dependency_overrides.get(
                param.default.dependency,
                param.default.dependency,
            ),
        )


def _resolve_sub_dependency_sync(
    sub_dependency: DependencyInfo,
    call_kwargs: dict[str, T],
    app_instance: FastAPI,
    exit_stack: ExitStack,
) -> T | None:
    if sub_dependency.name in call_kwargs:
        return call_kwargs[sub_dependency.name]
    if sub_dependency.dependency is not None:
        return _resolve_dependency_sync(
            cast(SyncDependency, sub_dependency.dependency),
            call_kwargs,
            app_instance,
            exit_stack,
        )
    return None


def _resolve_dependency_sync(
    dependency: SyncDependency[T],
    call_kwargs: dict[str, Any],
    app_instance: FastAPI,
    exit_stack: ExitStack,
) -> T:
    kwargs = {}
    for sub_dependency in _sub_dependencies(dependency, app_instance):
        resolved = _resolve_sub_dependency_sync(
            sub_dependency=sub_dependency,
            call_kwargs=call_kwargs,
            app_instance=app_instance,
            exit_stack=exit_stack,
        )
        if resolved is not None:
            kwargs[sub_dependency.name] = resolved

    return _call_dependency_sync(dependency, exit_stack, kwargs)


# TODO: Add check for positional only parameters
def _get_sync_wrapper(
    func: Callable[P, T],
) -> Callable[P, T]:

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        exit_stack = ExitStack()
        app_instance = _get_app_instance()
        call_kwargs = _get_call_kwargs(func, *args, **kwargs)

        return _resolve_dependency_sync(
            dependency=func,
            call_kwargs=call_kwargs,
            app_instance=app_instance,
            exit_stack=exit_stack,
        )

    return wrapper


async def _resolve_sub_dependency_async(
    sub_dependency: DependencyInfo,
    call_kwargs: dict[str, T],
    app_instance: FastAPI,
    async_exit_stack: AsyncExitStack,
) -> T | None:
    if sub_dependency.name in call_kwargs:
        return call_kwargs[sub_dependency.name]
    if sub_dependency.dependency is not None:
        return await _resolve_dependency_async(
            cast(AsyncDependency, sub_dependency.dependency),
            call_kwargs,
            app_instance,
            async_exit_stack,
        )
    return None


async def _resolve_dependency_async(
    dependency: AsyncDependency[T],
    call_kwargs: dict[str, Any],
    app_instance: FastAPI,
    async_exit_stack: AsyncExitStack,
) -> T:
    async with asyncer.create_task_group() as tg:
        soon_kwargs = {}
        for sub_dependency in _sub_dependencies(dependency, app_instance):
            soon_kwargs[sub_dependency.name] = tg.soonify(
                _resolve_sub_dependency_async,
            )(
                sub_dependency=sub_dependency,
                call_kwargs=call_kwargs,
                app_instance=app_instance,
                async_exit_stack=async_exit_stack,
            )
    kwargs = {
        name: soon_kwarg.value
        for name, soon_kwarg in soon_kwargs.items()
        if soon_kwarg.value is not None
    }

    return await _call_dependency_async(dependency, async_exit_stack, kwargs)


def _get_async_wrapper(
    func: Callable[P, Awaitable[T]],
) -> Callable[P, Awaitable[T]]:

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        async_exit_stack = AsyncExitStack()
        app_instance = _get_app_instance()
        call_kwargs = _get_call_kwargs(func, *args, **kwargs)

        return await _resolve_dependency_async(
            dependency=func,
            call_kwargs=call_kwargs,
            app_instance=app_instance,
            async_exit_stack=async_exit_stack,
        )

    return wrapper


@overload
def inject(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]: ...


@overload
def inject(func: Callable[P, T]) -> Callable[P, T]: ...


def inject(func: Callable[P, T]) -> Callable[P, T] | Callable[P, Awaitable[T]]:
    if inspect.iscoroutinefunction(func):
        return _get_async_wrapper(func)
    return _get_sync_wrapper(func)
