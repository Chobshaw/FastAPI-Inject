import pytest
from fastapi import FastAPI

from fastapi_inject._exceptions import NotEnabledError
from fastapi_inject.enable import _get_app_instance


def test_enabled(enabled_app: FastAPI):
    assert _get_app_instance() is enabled_app


def test_not_enabled(non_enabled_app: FastAPI):
    with pytest.raises(NotEnabledError):
        _get_app_instance()
