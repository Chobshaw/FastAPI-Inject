from fastapi import APIRouter, FastAPI

from fastapi_inject.injection import inject
from tests.code.functions import get_message, get_message_async

router = APIRouter()


@router.get("/sync")
def root() -> dict[str, str]:
    return {"message": inject(get_message)()}


@router.get("/async")
async def root_async() -> dict[str, str]:
    return {"message": await inject(get_message_async)()}


def get_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app
