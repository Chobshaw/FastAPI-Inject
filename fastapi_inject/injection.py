import functools
import inspect
from collections.abc import Awaitable, Callable
from contextlib import AsyncExitStack
from typing import Any, NamedTuple, ParamSpec, TypeVar, cast, overload

import fastapi
from fastapi import FastAPI
from fastapi.dependencies.utils import (
    is_async_gen_callable,
    is_coroutine_callable,
    is_gen_callable,
    solve_generator,
)
from starlette.concurrency import run_in_threadpool

T = TypeVar("T")
P = ParamSpec("P")

app_instance: FastAPI | None = None


class NotEnabledError(Exception):
    def __init__(self) -> None:
        super().__init__(
            "Injection must be enabled before using @inject. "
            "Please use enable_injection(app)"
        )


class DependencyInfo(NamedTuple):
    name: str
    dependency: Callable[..., Any]
    arg_position: int


def enable_injection(app: FastAPI) -> None:
    global app_instance  # noqa: PLW0603
    app_instance = app


def _is_provided(dep_info: DependencyInfo, args: tuple, kwargs: dict) -> bool:
    return dep_info.name in kwargs or (
        dep_info.arg_position != -1 and dep_info.arg_position < len(args)
    )


def _get_default_overrides(
    func: Callable[P, T | Awaitable[T]]
) -> dict[str, DependencyInfo]:
    default_overrides = {}
    for i, param in enumerate(inspect.signature(func).parameters.values()):
        if not isinstance(param.default, fastapi.params.Depends):
            continue
        if param.default.dependency is None:
            msg = (
                "Depends instance must have a dependency. "
                "Please add a dependency or use a type annotation"
            )
            raise ValueError(msg)
        default_overrides[param.name] = DependencyInfo(
            name=param.name,
            dependency=param.default.dependency,
            arg_position=-1 if param.kind == param.KEYWORD_ONLY else i,
        )
    return default_overrides


async def _resolve_dependency(
    dependency: Callable[[], T | Awaitable[T]], async_exit_stack: AsyncExitStack
) -> T:
    if is_gen_callable(dependency) or is_async_gen_callable(dependency):
        return await solve_generator(
            call=dependency, stack=async_exit_stack, sub_values={}
        )
    if is_coroutine_callable(dependency):
        return await cast(Awaitable[T], dependency())
    return await run_in_threadpool(cast(Callable[[], T], dependency))


def _get_async_wrapper(
    func: Callable[P, Awaitable[T]],
    default_overrides: dict[str, DependencyInfo],
) -> Callable[P, Awaitable[T]]:
    async_exit_stack = AsyncExitStack()

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        for name, info in default_overrides.items():
            if _is_provided(info, args, kwargs):
                continue
            if app_instance is None:
                raise NotEnabledError
            dependency = app_instance.dependency_overrides.get(
                info.dependency, info.dependency
            )
            kwargs[name] = await _resolve_dependency(
                dependency=dependency, async_exit_stack=async_exit_stack
            )
        return await func(*args, **kwargs)

    return wrapper


def _get_sync_wrapper(
    func: Callable[P, T], default_overrides: dict[str, DependencyInfo]
) -> Callable[P, T]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        for name, info in default_overrides.items():
            if _is_provided(info, args, kwargs):
                continue
            if app_instance is None:
                raise NotEnabledError
            dependency = app_instance.dependency_overrides.get(
                info.dependency, info.dependency
            )
            if inspect.iscoroutinefunction(info.dependency):
                msg = "Cannot inject async dependency into sync function"
                raise ValueError(msg)
            kwargs[name] = dependency()
        return func(*args, **kwargs)

    return wrapper


@overload
def inject(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
    ...


@overload
def inject(func: Callable[P, T]) -> Callable[P, T]:
    ...


def inject(func: Callable[P, T]) -> Callable[P, T] | Callable[P, Awaitable[T]]:
    default_overrides = _get_default_overrides(func)

    if inspect.iscoroutinefunction(func):
        return _get_async_wrapper(func, default_overrides)
    return _get_sync_wrapper(func, default_overrides)
