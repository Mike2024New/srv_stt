import asyncio
from queue import Empty
from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect
from config import Parameters
from engine.main import Engine


def routers_factory(engine: Engine) -> APIRouter:
    router = APIRouter()

    @router.get('/parameters/')
    def parameters():
        """Получить параметры модели. Узнать запущен ли движок."""
        return {
            'running': engine.is_running(),
            'parameters': engine.get_parameters(),
        }

    @router.post('/start/')
    async def start(input_parameters: Parameters):
        """Запуск движка с передачей параметров"""
        await engine.start(parameters=input_parameters)
        return {'result': 'Engine запущен'}

    @router.get('/stop/')
    async def stop():
        await engine.stop()
        return {'result': 'Engine остановлен'}

    @router.websocket('/ws')
    async def stream(websocket: WebSocket):
        """Стриминг для мгновенного получения распознанного текста (альтернатива поллингу)"""
        await websocket.accept()  # установить соединение с клиентом
        try:
            while engine.is_running():
                if not engine.is_running():
                    await websocket.close()
                    break
                try:
                    res = engine.queue.get_nowait()
                    if res is None:
                        break
                    await websocket.send_json(res)
                except Empty:
                    await asyncio.sleep(0.05)

        except WebSocketDisconnect:
            return
        finally:
            try:
                await websocket.close()
            except Exception:  # noqa
                pass

    return router
