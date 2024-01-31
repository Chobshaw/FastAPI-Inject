from fastapi import APIRouter, Depends, FastAPI

from fastapi_inject.injection import enable_injection, inject
from tests.dependencies import func, generator

router = APIRouter()


@inject
def get_message(message: str = Depends(func)):
    return message


@inject
def get_generator_message(message: str = Depends(generator)):
    return message


@router.get("/")
def get():
    return {"message": get_generator_message()}


def get_enabled_app():
    app = FastAPI()
    enable_injection(app)
    app.include_router(router)
    return app


def get_disabled_app():
    return FastAPI()


app = get_enabled_app()
