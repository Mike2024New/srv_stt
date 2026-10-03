import asyncio
import queue
import sounddevice as sd
from queue import Queue


class Engine:
    def __init__(self):
        self._running = False
        self._audio_input_stream = None
        self._event = asyncio.Event()
        self.queue = Queue(maxsize=200)

    def start(self, samplerate: int, blocksize: int):
        """Загрузка модели (тяжелых ресурсов)"""
        if self._running:
            return
        self._running = True

        # создание и запуск стриминга
        self._audio_input_stream = sd.InputStream(
            samplerate=samplerate,
            channels=1,
            dtype='float32',
            blocksize=blocksize,
            callback=self.callback,
        )
        self._audio_input_stream.start()

    def callback(self, indata, _frames, _time, _status):
        """Складывать сырые pcm чанки в очередь"""
        try:
            self.queue.put(indata, block=False)
        except queue.Full:  # если вдруг движок не вывозит чанки
            self.queue.get_nowait()
            self.queue.put(indata, block=False)

    def stop(self):
        if not self._running:
            return
        self._running = False
        self.queue.put_nowait(None)  # sentinel
        self._audio_input_stream.stop()
        self._audio_input_stream.close()
        self._audio_input_stream = None


if __name__ == '__main__':
    engine = Engine()
    engine.start(samplerate=16000, blocksize=1024)
    input('...')
    engine.stop()
