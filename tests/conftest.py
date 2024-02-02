from collections.abc import AsyncIterator

import anyio
import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from fastapi_inject.enable import _disable_injection, enable_injection
from tests.code.dependencies import async_function, sync_function
from tests.code.main import get_app

OVERRIDE_MESSAGE = "Goodbye World!"


@pytest.fixture()
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture()
def non_enabled_app() -> FastAPI:
    _disable_injection()
    return get_app()


@pytest.fixture()
def enabled_app(non_enabled_app: FastAPI) -> FastAPI:
    enable_injection(non_enabled_app)
    return non_enabled_app


@pytest.fixture()
async def client(enabled_app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(app=enabled_app, base_url="http://test") as client:
        yield client


@pytest.fixture()
async def app_with_dependency_overrides(enabled_app: FastAPI) -> FastAPI:
    def sync_function_override() -> str:
        return OVERRIDE_MESSAGE

    async def async_function_override() -> str:
        await anyio.sleep(0.1)
        return OVERRIDE_MESSAGE

    overrides = {
        sync_function: sync_function_override,
        async_function: async_function_override,
    }
    enabled_app.dependency_overrides.update(overrides)
    return enabled_app


@pytest.fixture()
async def overrides_client(
    app_with_dependency_overrides: FastAPI,
) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        app=app_with_dependency_overrides,
        base_url="http://test",
    ) as client:
        yield client
