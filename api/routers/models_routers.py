from fastapi import APIRouter
from engine.main import Engine
from config import settings


def routers_factory(engine: Engine) -> APIRouter:
    _ = engine
    router = APIRouter(prefix='/models', tags=['models'])

    @router.get('/')
    async def available_models_list():
        """Получить список доступных моделей"""
        models_list = []
        for file in settings.models_dir_prop.iterdir():
            for model in file.iterdir():
                models_list.append(model.name)
        return {'models_list': models_list}

    return router
