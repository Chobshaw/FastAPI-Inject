import functools
import inspect
from collections.abc import Awaitable, Callable
from contextlib import AsyncExitStack, ExitStack
from typing import Any, Iterator, NamedTuple, ParamSpec, TypeVar, overload

import anyio
from fastapi import FastAPI
from fastapi.params import Depends

from ._exceptions import NotEnabledError
from .utils import Dependency, _resolve_dependency_async, _resolve_dependency_sync

T = TypeVar("T")
P = ParamSpec("P")

app_instance: FastAPI | None = None


def enable_injection(app: FastAPI) -> None:
    global app_instance  # noqa: PLW0603
    app_instance = app


class DependencyInfo(NamedTuple):
    name: str
    dependency: Callable[..., Any]
    arg_position: int


def _is_provided(dep_info: DependencyInfo, args: tuple, kwargs: dict) -> bool:
    return dep_info.name in kwargs or (
        dep_info.arg_position != -1 and dep_info.arg_position < len(args)
    )


def _get_dependencies(func: Callable[P, T | Awaitable[T]]) -> list[DependencyInfo]:
    dependencies = []
    for i, param in enumerate(inspect.signature(func).parameters.values()):
        if not isinstance(param.default, Depends):
            continue
        if param.default.dependency is None:
            msg = (
                "Depends instance must have a dependency. "
                "Please add a dependency or use a type annotation"
            )
            raise ValueError(msg)
        dependencies.append(
            DependencyInfo(
                name=param.name,
                dependency=param.default.dependency,
                arg_position=-1 if param.kind == param.KEYWORD_ONLY else i,
            )
        )
    return dependencies


def _dependencies(
    dependencies: list[DependencyInfo], args: tuple, kwargs: dict
) -> Iterator[tuple[str, Dependency]]:
    if app_instance is None:
        raise NotEnabledError
    for dependency_info in dependencies:
        if _is_provided(dependency_info, args, kwargs):
            continue
        dependency = app_instance.dependency_overrides.get(
            dependency_info.dependency, dependency_info.dependency
        )
        yield dependency_info.name, dependency


def _get_sync_wrapper(
    func: Callable[P, T], dependencies: list[DependencyInfo]
) -> Callable[P, T]:
    exit_stack = ExitStack()

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        for name, dependency in _dependencies(dependencies, args, kwargs):
            kwargs[name] = _resolve_dependency_sync(
                dependency=dependency, exit_stack=exit_stack
            )
        return func(*args, **kwargs)

    return wrapper


def _get_async_wrapper(
    func: Callable[P, Awaitable[T]],
    dependencies: list[DependencyInfo],
) -> Callable[P, Awaitable[T]]:
    async_exit_stack = AsyncExitStack()

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        async with anyio.create_task_group() as tg:
            for name, dependency in _dependencies(dependencies, args, kwargs):
                kwargs[name] = tg.start_soon(
                    _resolve_dependency_async, dependency, async_exit_stack
                )
        return await func(*args, **kwargs)

    return wrapper


@overload
def inject(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
    ...


@overload
def inject(func: Callable[P, T]) -> Callable[P, T]:
    ...


def inject(func: Callable[P, T]) -> Callable[P, T] | Callable[P, Awaitable[T]]:
    dependencies = _get_dependencies(func)

    if inspect.iscoroutinefunction(func):
        return _get_async_wrapper(func, dependencies)
    return _get_sync_wrapper(func, dependencies)
