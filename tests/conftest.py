import pytest
from fastapi import FastAPI

from fastapi_inject.enable import _disable_injection, enable_injection
from fastapi_inject.injection import _get_dependencies
from tests.code.functions import get_messages_async


@pytest.fixture()
def anyio_backend():
    return "asyncio"


@pytest.fixture()
def non_enabled_app():
    _disable_injection()
    return FastAPI()


@pytest.fixture()
def enabled_app(non_enabled_app: FastAPI):
    enable_injection(non_enabled_app)
    return non_enabled_app


@pytest.fixture()
def dependencies_info():
    return _get_dependencies(get_messages_async)
