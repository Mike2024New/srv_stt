import asyncio, subprocess, zipfile
import warnings
import sys

"""
Скрипт установки и сборки проекта.
Требуется виртуальное окружение в папке .venv

Все шаги (простая установка после клонирования с git):     python start.py all
По отдельности:
  sync        - установить зависимости
  dwn         - скачать материалы
  build       - собрать .exe/bin
"""
args = sys.argv


async def start():
    if 'sync' in args or 'all' in args:
        if 'all' in args:
            print(f'Установка uv и зависимостей', flush=True)
        cmd = [sys.executable, '-m', 'pip', 'install', 'uv']
        subprocess.run(cmd, shell=False)
        cmd = [sys.executable, '-m', 'uv', 'sync']
        subprocess.run(cmd, shell=False)

    if 'dwn' in args or 'all' in args:
        if 'all' in args:
            print(f'Загрузка дополнительных материалов', flush=True)
        from infrastructure_http_clients import file_downloader, DownloadFileType
        from config import settings

        download_list = [
            DownloadFileType(
                url_list=[
                    'https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip',
                    'https://github.com/Mike2024New/STT_OFFLINE/releases/download/v1.1.0/vosk-model-small-ru-0.22.zip',
                ],
                target_dir=settings.vosk_models_dir_prop,
                filename='vosk-model-small-ru-0.22.zip',
                replace=False,
            ),
            DownloadFileType(
                url_list=[
                    'https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip',
                    'https://github.com/Mike2024New/STT_OFFLINE/releases/download/v1.1.0/vosk-model-small-en-us-0.15.zip',
                ],
                target_dir=settings.vosk_models_dir_prop,
                filename='vosk-model-small-en-us-0.15.zip',
                replace=False,
            ),

            # загрузка small модели для whisper
            DownloadFileType(
                url_list=[
                    'https://huggingface.co/Systran/faster-whisper-small/resolve/main/config.json',
                    'https://huggingface.co/Systran/faster-whisper-small/resolve/main/tokenizer.json',
                    'https://huggingface.co/Systran/faster-whisper-small/resolve/main/model.bin',
                    'https://huggingface.co/Systran/faster-whisper-small/resolve/main/vocabulary.txt',
                ],
                target_dir=settings.whisper_models_dir_prop / 'small',
                filename='whisper-small',
            ),

        ]
        await file_downloader(download_list=download_list, console_progress_bar=True)

        for model in ('vosk-model-small-ru-0.22.zip', 'vosk-model-small-en-us-0.15.zip'):
            zip_path = settings.vosk_models_dir_prop / model
            if not zip_path.exists():
                warnings.warn(f'Не удалось скачать модель {model}')
                continue

            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(settings.vosk_models_dir_prop)  # noqa
            zip_path.unlink()

    if 'build' in args or 'all' in args:
        if 'all' in args:
            print(f'Сборка .exe/bin', flush=True)
        from build import build, parameters
        build(parameters=parameters)


if __name__ == '__main__':
    asyncio.run(start())
