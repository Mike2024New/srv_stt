import asyncio, subprocess, aiohttp, websockets, json, sys
from pathlib import Path
from infrastructure_http_clients import ServerProbe

port = 8000


async def run_server() -> subprocess.Popen:
    # 1.запустить сервер
    cmd = [sys.executable, 'cli.py', 'run-server', '--port', str(port), '--log-level', 'info']
    process = subprocess.Popen(cmd, cwd=Path.cwd())

    # 2. Ожидание запуска сервера (пока сервер не станет отвечать на /health/, например torch загружается долго)
    print(f'Ожидание запуска сервера')
    ServerProbe.wait_for_server_up(
        url=f'http://127.0.0.1:{port}/health/',
        timeout=30,
        expected_status=200,
    )

    # 3. Запуск engine, с переданными параметрами модели
    async with aiohttp.ClientSession() as session:
        parameters = {
            'samplerate': 16000, 'blocksize': 1024, 'model': 'small',  # прямо здесь можно указывать whisper
        }
        print(f'Запуск engine сервера')
        async with session.post(url=f'http://127.0.0.1:{port}/start/', json=parameters) as resp:
            answer = await resp.json()
            print(answer)
            assert resp.status == 200, f'Engine сервера не был запущен.'
    return process


async def example():
    """
    Подключение к сокету и получение данных реал-тайм
    """
    async with websockets.connect(f'ws://127.0.0.1:{port}/ws') as ws:  # установка соединения
        event = asyncio.Event()  # флаг выхода
        try:
            async def consumer():
                while not event.is_set():
                    try:
                        # во избежание зависания стриминга желательно использовать wait_for
                        data = await asyncio.wait_for(ws.recv(), timeout=0.1)
                        data = json.loads(data)  # пример: {'type': 'result', 'text': 'распознанный текст'}
                        print(data)  # обработка полученной фразы
                    except asyncio.TimeoutError:
                        pass

            task = asyncio.create_task(consumer())
            print(f'Говорите, что нибудь, через 10 секунд компонент отключится.')
            await asyncio.sleep(10)
            event.set()
            await task

        except websockets.exceptions.ConnectionClosedOK:
            event.set()  # соединение закрыто штатно, всё в порядке, не логировать

        except Exception as err:  # обработка ошибки, логировать
            print(f'Ошибка соединения {err}')
            event.set()


async def graceful_shutdown(process: subprocess.Popen):
    """Аккуратная остановка сервера"""
    async with aiohttp.ClientSession() as session:
        # остановить engine сервера (высвобождение памяти)
        print(f'Остановка engine сервера')
        async with session.get(url=f'http://127.0.0.1:{port}/stop/') as resp:
            assert resp.status == 200, f'Engine сервера не был остановлен.'
        # остановить сервер
        print(f'Остановка сервера')
        async with session.get(url=f'http://127.0.0.1:{port}/shutdown/') as resp:
            assert resp.status == 200, f'Сервер не был остановлен.'

    # 5. Убедиться что процесс завершился
    process.wait(timeout=10)


async def main():
    process = await run_server()  # запуск сервера и движка
    await example()  # пример взаимодействия с сервером (получение распознанного текста реал-тайм)
    await graceful_shutdown(process=process)  # аккуратная остановка сервера


if __name__ == '__main__':
    asyncio.run(main())
