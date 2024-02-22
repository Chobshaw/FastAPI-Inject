from typing import Any

import pytest
from fastapi import Depends, FastAPI
from httpx import AsyncClient

from fastapi_inject.injection import (
    _get_call_kwargs,
    _get_sync_wrapper,
    _sub_dependencies,
    inject,
)
from tests.code.dependencies import (
    MESSAGE,
    async_function,
    async_generator,
    sync_function,
    sync_generator,
)
from tests.code.functions import (
    get_message,
    get_message_no_deps,
    get_messages_async,
    get_messages_mixed_deps,
    get_messages_sync,
    get_personalised_message_async,
    get_personalised_message_sync,
)
from tests.conftest import OVERRIDE_MESSAGE


@pytest.mark.parametrize(
    ("args", "kwargs", "expected_result"),
    [
        ((10, "world"), {}, {"a": 10, "b": "world"}),
        ((10,), {"b": "world"}, {"a": 10, "b": "world"}),
        ((), {"a": 10, "b": "world"}, {"a": 10, "b": "world"}),
        ((), {"a": 10}, {"a": 10, "b": "hello"}),
    ],
)
def test_get_call_kwargs(
    args: tuple,
    kwargs: dict[str, Any],
    expected_result: dict[str, Any],
) -> None:
    def my_func(a: int, b: str = "hello") -> None:
        pass

    assert _get_call_kwargs(my_func, *args, **kwargs) == expected_result


def test_sub_dependencies(enabled_app: FastAPI):
    dependencies = [sync_function, async_function, sync_generator, async_generator]
    for i, sub_dependency in enumerate(
        _sub_dependencies(get_messages_async, enabled_app),
    ):
        assert sub_dependency.name == f"message_{i + 1}"
        assert sub_dependency.dependency == dependencies[i]

    for sub_dependency in _sub_dependencies(get_message_no_deps, enabled_app):
        assert sub_dependency.name == "message"
        assert sub_dependency.dependency is None


def test_sub_dependencies_missing_dependency(enabled_app: FastAPI):
    def get_message_missing_dep(message: str = Depends()) -> str:
        return message  # pragma: no cover

    with pytest.raises(  # noqa: PT012
        ValueError,
        match=(
            "Depends instance must have a dependency. "
            "Please add a dependency or use a type annotation"
        ),
    ):
        for sub_dependency in _sub_dependencies(get_message_missing_dep, enabled_app):
            assert sub_dependency.name == "message"  # pragma: no cover


@pytest.mark.anyio()
async def test_sub_dependencies_with_overrides(app_with_dependency_overrides: FastAPI):
    async def get_messages(
        message_1: str = Depends(sync_function),
        message_2: str = Depends(async_function),
    ) -> list[str]:
        return [message_1, message_2]  # pragma: no cover

    for sub_dependency in _sub_dependencies(
        get_messages,
        app_with_dependency_overrides,
    ):
        assert sub_dependency.name in ["message_1", "message_2"]
        assert sub_dependency.dependency not in [sync_function, async_function]


def test_inject_sync(enabled_app: FastAPI):
    assert inject(get_message)() == MESSAGE
    assert inject(get_message_no_deps)(MESSAGE) == MESSAGE
    assert inject(get_messages_sync)() == [MESSAGE, MESSAGE]
    assert inject(get_messages_sync)(MESSAGE) == [MESSAGE, MESSAGE]
    assert inject(get_messages_sync)(message_1=MESSAGE) == [MESSAGE, MESSAGE]
    assert inject(get_personalised_message_sync)(name="John") == "Hello John!"

    error_msg = "Cannot inject async dependency into sync function"
    with pytest.raises(ValueError, match=error_msg):
        _get_sync_wrapper(get_messages_async)()  # type: ignore[unused-coroutine]


@pytest.mark.anyio()
async def test_inject_async(enabled_app: FastAPI):
    assert await inject(get_messages_async)() == [MESSAGE, MESSAGE, MESSAGE, MESSAGE]
    assert await inject(get_messages_mixed_deps)(message_1=MESSAGE) == [
        MESSAGE,
        MESSAGE,
        MESSAGE,
    ]
    assert await inject(get_personalised_message_async)(name="John") == "Hello John!"


@pytest.mark.anyio()
async def test_inject_in_app(client: AsyncClient):
    response = await client.get("/sync")
    assert response.json().get("message") == MESSAGE

    response = await client.get("/async")
    assert response.json().get("message") == MESSAGE


@pytest.mark.anyio()
async def test_inject_in_app_with_overrides(overrides_client: AsyncClient):
    response = await overrides_client.get("/sync")
    assert response.json().get("message") == OVERRIDE_MESSAGE

    response = await overrides_client.get("/async")
    assert response.json().get("message") == OVERRIDE_MESSAGE
