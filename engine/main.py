import queue
import uuid, asyncio, numpy, threading
from engine.audio_input_engine import Engine as AudioInputEngine
from engine.stt_vosk_engine import Engine as SttVoskEngine
from engine.stt_whisper_engine import Engine as SttWhisperEngine
from config.schemas import Parameters
from queue import Queue, Empty
from collections import deque
from time import perf_counter


class Engine:
    def __init__(self):
        self._running = False
        self._parameters: Parameters | None = None
        self._audio_engine: AudioInputEngine | None = None
        self._stt_vosk_engine: SttVoskEngine | None = None
        self._stt_whisper_engine: SttWhisperEngine | None = None
        self.queue = Queue()  # основная очередь для потребителя (например для стриминга) сюда stt сложат результаты
        # буферы накопители для whisper
        self._whisper_prebuffer = deque(maxlen=200)
        self._whisper_buffer = deque(maxlen=1000)
        # переменные события, для управления отправкой текста на распознавание в whisper
        self.whisper_speech_start_event = asyncio.Event()
        self.whisper_speech_end_event = asyncio.Event()
        self.is_speech = False  # вспомогательный флаг для whisper
        self._speech_request_id = None
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
            self._audio_engine = AudioInputEngine()
            self._stt_vosk_engine = SttVoskEngine()
            # vosk модель инициализируется всегда (она как vad)
            self._stt_vosk_engine.start(model='vosk-model-small-ru-0.22', samplerate=parameters.samplerate)
            self._audio_engine.start(samplerate=self._parameters.samplerate, blocksize=self._parameters.blocksize)
            print(f'Движок запущен')

            # если опционально указана модель whisper на входе
            if SttWhisperEngine.is_available_model(self._parameters.model):
                self._stt_whisper_engine = SttWhisperEngine()
                self._stt_whisper_engine.start(model=self._parameters.model, samplerate=parameters.samplerate)

            # запуск воркера
            threading.Thread(target=lambda: self.stt_worker(), daemon=True).start()

    def stt_worker(self):
        """Закидывает распознанные фразы в очередь"""
        while self._running:
            try:
                indata = self._audio_engine.queue.get(block=True)
                if indata is None:  # sentinel выход
                    break
            except queue.Empty:
                continue

            pcm = indata[:, 0].copy()  # текущий входной чанк аудио
            if not self.is_speech:  # если сейчас не идет речь (иными словами запись пошла уже в речевой буфер)
                self._whisper_prebuffer.append(pcm)  # положить его в ограниченный буфер (он пишет всё)

            if self._running:
                # обработка для whisper
                if self._stt_whisper_engine is not None:
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
                                            'metric_sec': round(perf_counter() - self._start_time, 4),
                                            'request_id': self._speech_request_id,

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
                    self.is_speech = False
                    self.whisper_speech_end_event.set()

                    end_time = round(perf_counter() - self._start_time, 4)
                    res.update({'metric_sec': end_time, 'request_id': self._speech_request_id})
                    self.queue.put(res)

                # начали говорить (первый partial - ориентир, и для whisper который захватывает часть предбуфера)
                if res.get('type') == 'partial':
                    if not self.is_speech:
                        self.is_speech = True
                        self.whisper_speech_start_event.set()
                        self._speech_request_id = str(uuid.uuid4())[:8]
                        self._start_time = perf_counter()
                    res.update({'request_id': self._speech_request_id})
                    self.queue.put(res)

    async def stop(self):
        if self._running:
            print(f'Остановка движка (подождите)')
            self._running = False
            self._audio_engine.stop()  # sentinel для воркера
            self._stt_vosk_engine.stop()
            if self._stt_whisper_engine is not None:
                self._stt_whisper_engine.stop()
            self._parameters = None
            self.queue = Queue()
            print(f'Движок остановлен')


async def main():
    engine = Engine()
    engine_task = asyncio.create_task(engine.start(parameters=Parameters(model='small')))

    async def consumer():
        while engine.is_running():
            try:
                res = engine.queue.get_nowait()
                if res.get('type', None) == 'result':
                    print(res)
                # elif res.get('type', None) == 'partial':
                #     print(res)
            except Empty:
                await asyncio.sleep(0.05)

    consumer_task = asyncio.create_task(consumer())
    await asyncio.to_thread(lambda: input('... press enter for exit ...\n'))
    await engine.stop()
    await engine_task
    await consumer_task


if __name__ == '__main__':
    asyncio.run(main())
