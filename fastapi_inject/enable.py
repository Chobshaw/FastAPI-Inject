from fastapi import FastAPI

from ._exceptions import NotEnabledError

app_instance: FastAPI | None = None


def enable_injection(app: FastAPI) -> None:
    global app_instance  # noqa: PLW0603
    app_instance = app


def _disable_injection() -> None:
    global app_instance  # noqa: PLW0603
    app_instance = None


def _get_app_instance() -> FastAPI:
    if app_instance is None:
        raise NotEnabledError
    return app_instance
