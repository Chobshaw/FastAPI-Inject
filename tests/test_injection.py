import pytest
from fastapi import Depends, FastAPI
from httpx import AsyncClient

from fastapi_inject.injection import (
    DependencyInfo,
    _dependencies,
    _get_dependencies,
    _get_sync_wrapper,
    _is_provided,
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
)
from tests.conftest import OVERRIDE_MESSAGE


def test_is_provided():
    dependency = lambda: MESSAGE  # noqa: E731
    dep_info = DependencyInfo(name="dependency", dependency=dependency, arg_position=0)

    assert _is_provided(dep_info, [], {"dependency": MESSAGE})
    assert _is_provided(dep_info, [MESSAGE], {})
    assert not _is_provided(dep_info, [], {})

    kw_only_dep_info = DependencyInfo(
        name="dependency",
        dependency=dependency,
        arg_position=-1,
    )

    assert not _is_provided(kw_only_dep_info, [MESSAGE], {})


def test_get_dependencies():
    # Test no dependencies
    dependencies = _get_dependencies(get_message_no_deps)
    assert len(dependencies) == 0

    # Test mixed dependencies
    dependencies = _get_dependencies(get_messages_mixed_deps)
    assert len(dependencies) == 2
    assert dependencies[0] == DependencyInfo(
        name="message_2",
        dependency=async_function,
        arg_position=1,
    )

    # Test all dependencies
    dependencies = _get_dependencies(get_messages_async)
    assert len(dependencies) == 4
    assert dependencies[0] == DependencyInfo(
        name="message_1",
        dependency=sync_function,
        arg_position=0,
    )

    # Test missing dependency
    def get_message_missing_dependency(message: str = Depends()) -> str:
        return message  # pragma: no cover

    error_msg = (
        "Depends instance must have a dependency. "
        "Please add a dependency or use a type annotation"
    )
    with pytest.raises(ValueError, match=error_msg):
        _get_dependencies(get_message_missing_dependency)


def test_dependencies_generator(
    enabled_app: FastAPI,
):
    dependencies = [sync_function, async_function, sync_generator, async_generator]
    dependencies_info = _get_dependencies(get_messages_async)

    # Test generator
    i = 0
    for name, dependency in _dependencies(
        dependencies=dependencies_info,
        args=(),
        kwargs={},
    ):
        assert name == f"message_{i + 1}"
        assert dependency == dependencies[i]
        i += 1

    # Test generator with provided arg dependency
    i = 2
    for name, dependency in _dependencies(
        dependencies=dependencies_info,
        args=(MESSAGE, MESSAGE),
        kwargs={},
    ):
        assert name == f"message_{i + 1}"
        assert dependency == dependencies[i]
        i += 1

    # Test generator with provided kwarg dependency
    i = 0
    for name, dependency in _dependencies(
        dependencies=dependencies_info,
        args=(),
        kwargs={"message_4": MESSAGE},
    ):
        assert name == f"message_{i + 1}"
        assert dependency == dependencies[i]
        i += 1


def test_inject_sync(enabled_app: FastAPI):
    assert inject(get_message)() == MESSAGE
    assert inject(get_message_no_deps)(MESSAGE) == MESSAGE
    assert inject(get_messages_sync)() == [MESSAGE, MESSAGE]
    assert inject(get_messages_sync)(MESSAGE) == [MESSAGE, MESSAGE]
    assert inject(get_messages_sync)(message_1=MESSAGE) == [MESSAGE, MESSAGE]

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
