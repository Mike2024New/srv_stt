import asyncio, numpy
import threading

from engine.audio_input_engine import Engine as AudioInputEngine
from engine.stt_vosk_engine import Engine as SttVoskEngine
from engine.stt_whisper_engine import Engine as SttWhisperEngine
from config.schemas import Parameters
from queue import Queue, Empty
from collections import deque
from time import perf_counter


class Engine:
    def __init__(self):
        self._audio_engine = AudioInputEngine()
        self._stt_vosk_engine = SttVoskEngine()
        self._stt_whisper_engine = SttWhisperEngine()
        self.queue = Queue()
        self._running = False
        self._parameters: Parameters | None = None
        # буферы накопители для whisper
        self._whisper_prebuffer = deque(maxlen=500)
        self._whisper_buffer = deque(maxlen=1000)
        # переменные события, для управления отправкой текста на распознавание в whisper
        self.whisper_speech_start_event = asyncio.Event()
        self.whisper_speech_end_event = asyncio.Event()
        self.is_speech = False
        # self._whisper_silence_limit = 10
        # self._whisper_silence_counter = 0
        self._start_time = None

    def is_running(self):
        """Статус движка, запущен ли?"""
        return self._running

    def get_parameters(self):
        """Получить текущие параметры"""
        return self._parameters

    async def start(self, parameters: Parameters):
        """Запуск микрофона с распознавателем речи"""
        if not self._running:
            print(f'Запуск движка (подождите)')
            self._running = True
            self._parameters = parameters
            if self._parameters.whisper_model_enable:
                self._stt_whisper_engine.start(parameters=self._parameters)
            self._stt_vosk_engine.start(parameters=self._parameters)
            self._audio_engine.start(
                parameters=self._parameters,
                callback=self.stt_callback,
            )

            print(f'Движок запущен')

    def stt_callback(self, indata, _frames, _time, _status):
        """Закидывает распознанные фразы в очередь"""

        pcm = indata[:, 0].copy()  # текущий входной чанк аудио
        self._whisper_prebuffer.append(pcm)  # положить его в ограниченный буфер (он пишет всё)

        if self._running:
            # обработка для whisper
            if self._parameters.whisper_model_enable:
                if self.whisper_speech_start_event.is_set():  # начали речь
                    self.whisper_speech_start_event.clear()
                    self._whisper_buffer.extend(self._whisper_prebuffer)
                    self._whisper_prebuffer.clear()

                if self.whisper_speech_end_event.is_set():
                    self.whisper_speech_end_event.clear()
                    if self._whisper_buffer:
                        chunks = numpy.concatenate(self._whisper_buffer)
                        self._whisper_buffer.clear()  # сбросить буфер (до длительной операции распознавания)
                        _result_buffer = numpy.concatenate((
                            numpy.zeros(100, dtype=numpy.float32), chunks, numpy.zeros(100, dtype=numpy.float32)
                        ))

                        def stt_whisper_worker():
                            result = self._stt_whisper_engine.process(pcm=_result_buffer)
                            if result:
                                self.queue.put(
                                    {
                                        'type': 'result',
                                        'text': result, 'engine': 'whisper',
                                        'metric_sec': round(perf_counter() - self._start_time, 4)
                                    }
                                )

                        threading.Thread(target=lambda: stt_whisper_worker()).start()

                # если сейчас говорят то пополнять буфер
                if self.is_speech:
                    self._whisper_buffer.append(pcm)

            # обработка для vosk
            indata_int16 = (indata * 32768).astype(numpy.int16)
            chunk_bytes = indata_int16.tobytes()
            res = self._stt_vosk_engine.recognized(chunk=chunk_bytes)
            # результат от vosk
            if res.get('type') == 'result':
                # если подключен whisper
                if self._parameters.whisper_model_enable:
                    self.is_speech = False
                    self.whisper_speech_end_event.set()

                # если whisper подключен, то его результат будет отправлен
                if not self._parameters.whisper_model_enable:
                    end_time = round(perf_counter() - self._start_time, 4)
                    res.update({'metric_sec': end_time})
                    self.queue.put(res)

            # начали говорить (первый partial - ориентир, и для whisper который захватывает часть предбуфера)
            if res.get('type') == 'partial':
                # если подключен whisper
                if self._parameters.whisper_model_enable:
                    self.is_speech = True
                    self.whisper_speech_start_event.set()
                self._start_time = perf_counter()
                self.queue.put(res)

    async def stop(self):
        if self._running:
            print(f'Остановка движка (подождите)')
            self._running = False
            self._audio_engine.stop()
            self._stt_vosk_engine.stop()
            self._stt_whisper_engine.stop()
            self._parameters = None
            self.queue = Queue()
            print(f'Движок остановлен')


async def main():
    engine = Engine()
    engine_task = asyncio.create_task(
        engine.start(
            parameters=Parameters(
                whisper_model_select='medium',  # выбор модели
                whisper_model_enable=True,  # whisper можно отключить
            )
        )
    )

    async def consumer():
        while engine.is_running():
            try:
                res = engine.queue.get_nowait()
                if res.get('type', None) == 'result':
                    print(res)
            except Empty:
                await asyncio.sleep(0.05)

    consumer_task = asyncio.create_task(consumer())
    await asyncio.to_thread(lambda: input('... press enter for exit ...\n'))
    await engine.stop()
    await engine_task
    await consumer_task


if __name__ == '__main__':
    asyncio.run(main())
