import asyncio
import numpy as np
import sounddevice as sd


class Engine:
    def __init__(self):
        self._running = False
        self._audio_input = None
        self._event = asyncio.Event()

    def start(self, samplerate: int, blocksize: int, callback):
        """Загрузка модели (тяжелых ресурсов)"""
        # создание стриминга
        if self._running:
            return
        self._running = True
        self._audio_input = sd.InputStream(
            samplerate=samplerate,
            channels=1,
            dtype='float32',
            blocksize=blocksize,
            callback=callback,
        )
        self._audio_input.start()

    def stop(self):
        if not self._running:
            return
        self._running = False
        self._audio_input.stop()
        self._audio_input.close()
        self._audio_input = None


if __name__ == '__main__':
    def callback(indata, _frames, _time, _status):
        if np.abs(indata).mean() < 0.03:
            print(f'Тихо')
        else:
            print(f'Шумно')


    engine = Engine()
    engine.start(samplerate=16000, blocksize=1024, callback=callback)
    input('...')
    engine.stop()
