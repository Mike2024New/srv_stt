import asyncio
import numpy as np
import sounddevice as sd

from config import Parameters


class Engine:
    def __init__(self):
        self._audio_input = None
        self._event = asyncio.Event()
        self._parameters: Parameters | None = None

    def is_running(self):
        """Статус движка, запущен ли?"""
        return self._audio_input is not None

    def get_parameters(self):
        """Получить текущие параметры"""
        return self._parameters

    def start(self, parameters: Parameters, callback):
        """Загрузка модели (тяжелых ресурсов)"""
        self._parameters = parameters
        # создание стриминга
        self._audio_input = sd.InputStream(
            samplerate=parameters.samplerate,
            channels=1,
            dtype='float32',
            blocksize=parameters.blocksize,
            callback=callback,
        )
        self._audio_input.start()

    def stop(self):
        if self._audio_input is not None:
            self._audio_input.stop()
            self._audio_input.close()
            self._audio_input = None
        self._parameters = None


if __name__ == '__main__':
    def callback(indata, _frames, _time, _status):
        if np.abs(indata).mean() < 0.03:
            print(f'Тихо')
        else:
            print(f'Шумно')


    engine = Engine()
    engine.start(parameters=Parameters(), callback=callback)
    input('...')
    engine.stop()
