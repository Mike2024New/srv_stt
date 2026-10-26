import queue
import uuid, asyncio, numpy, threading
from engine.audio_input_engine import Engine as AudioInputEngine
from engine.stt_vosk_engine import Engine as SttVoskEngine
from engine.stt_whisper_engine import Engine as SttWhisperEngine
from config.schemas import Parameters
from queue import Queue, Empty
from collections import deque
from time import perf_counter
from config import logger


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
        self._engines_count = 0
        self._engines_list = []

    def is_running(self):
        """Статус движка, запущен ли?"""
        return self._running

    def get_parameters(self):
        """Получить текущие параметры"""
        return self._parameters

    async def start(self, parameters: Parameters, request_id: str):
        """Запуск микрофона с распознавателем речи"""
        if not self._running:
            logger.set_logger(request_id=request_id)
            logger.info(f'Запуск engine')
            logger.debug(parameters.model_dump())  # логирование параметров запуска
            self._running = True
            self._parameters = parameters
            self._audio_engine = AudioInputEngine()
            self._stt_vosk_engine = SttVoskEngine()
            try:
                # vosk модель инициализируется всегда (она как vad)
                self._stt_vosk_engine.start(model='vosk-model-small-ru-0.22', samplerate=parameters.samplerate)
                self._engines_list.append('vosk')
                self._audio_engine.start(samplerate=self._parameters.samplerate, blocksize=self._parameters.blocksize)
            except Exception as err:
                logger.exception(f"Ошибка при запуске engine, не удаётся запустить vosk: {err}")

            # если опционально указана модель whisper на входе
            if SttWhisperEngine.is_available_model(self._parameters.model):
                try:
                    self._stt_whisper_engine = SttWhisperEngine()
                    self._stt_whisper_engine.start(model=self._parameters.model, samplerate=parameters.samplerate)
                    self._engines_list.append('whisper')
                except Exception as err:
                    logger.exception(f"Ошибка при запуске engine, не удаётся запустить whisper: {err}")

            # сообщить клиенту о количестве движков (сколько распознанных фраз ему ждать)
            self.queue.put(
                {'type': 'metadata', 'engines': self._engines_list},
                block=False
            )
            # запуск воркера
            threading.Thread(target=lambda: self.stt_worker(), daemon=True).start()
            logger.info(f'engine запущен')

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
                                try:
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
                                except Exception as e:
                                    logger.error(f'Ошибка при распознавании речи whisper: {e}')

                            threading.Thread(target=lambda: stt_whisper_worker()).start()

                    # если сейчас говорят то пополнять буфер
                    if self.is_speech:
                        self._whisper_buffer.append(pcm)

                # обработка для vosk
                indata_int16 = (indata * 32768).astype(numpy.int16)
                chunk_bytes = indata_int16.tobytes()
                try:
                    res = self._stt_vosk_engine.recognized(chunk=chunk_bytes)
                except Exception as err:
                    logger.exception(f'Ошибка при распознавании речи vosk: {err}')
                    continue
                # результат от vosk
                if res.get('type') == 'result':
                    self.is_speech = False
                    self.whisper_speech_end_event.set()

                    end_time = round(perf_counter() - self._start_time, 4)
                    res.update({
                        'metric_sec': end_time,
                        'request_id': self._speech_request_id,
                    })
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
            logger.info(f'Остановка engine')
            self._running = False
            try:
                self._audio_engine.stop()  # sentinel для воркера
            except Exception as err:
                logger.exception(f'Ошибка при остановке audio_input: {err}')
            try:
                self._stt_vosk_engine.stop()
            except Exception as err:
                logger.exception(f'Ошибка при остановке engine vosk: {err}')
            if self._stt_whisper_engine is not None:
                try:
                    self._stt_whisper_engine.stop()
                except Exception as err:
                    logger.exception(f'Ошибка при остановке engine whisper: {err}')
            self._parameters = None
            self.queue = Queue()
            logger.info(f'engine остановлен')


async def main():
    # vosk гарантированно всегда приходит первым
    engine = Engine()
    engine_task = asyncio.create_task(
        engine.start(parameters=Parameters(model='large-v3'), request_id='#001'))

    async def consumer():
        # Настройки
        whisper_timeout_sec = 2.0
        # удобно с точки зрения фильтрации ключевых слов в начале распознанного текста
        priority_words = ('джарвис', 'компьютер', 'ви', 'шарик')

        # Состояние текущей фразы
        current_request_id = None
        current_answers = []
        vosk_received_at = None  # время получения ответа от Vosk

        def reset_state():
            """Сброс состояния после обработки фразы."""
            nonlocal current_request_id, current_answers, vosk_received_at
            current_request_id = None
            current_answers = []
            vosk_received_at = None

        def process_final_answers(answers: list):
            """Единая точка отправки ответа в пайплайн (LLM/TTS)."""
            print(answers)  # TODO: заменить на вызов пайплайна

        def is_priority_command(text_in: str) -> bool:
            """Проверяет, начинается ли фраза с кодового слова."""
            for i in priority_words:
                first_word = text_in.split()[0].lower() if text_in else ''
                if first_word.lower() == i.lower():
                    return True
            return False

        while engine.is_running():
            try:
                res = engine.queue.get_nowait()
            except Empty:
                res = None

            if res is not None:
                msg_type = res.get('type')

                if msg_type == 'metadata':
                    if 'whisper' not in res.get('engines') and whisper_timeout_sec != 0:
                        # whisper отсутствует в движках, ждать нет смысла, занулить таймаут
                        whisper_timeout_sec = 0
                        logger.info("Whisper не обнаружен, таймаут whisper_timeout_sec отключен")

                # здесь можно обработать начало речи
                elif msg_type == 'partial':
                    pass

                elif msg_type == 'result':
                    engine_name = res.get('engine')
                    request_id = res.get('request_id')

                    # --- Vosk ---
                    if engine_name == 'vosk':
                        current_request_id = request_id
                        vosk_received_at = perf_counter()
                        current_answers = [res]

                        if is_priority_command(res.get('text', '')):
                            # Команда: обрабатывать сразу, Whisper не ждать
                            process_final_answers(current_answers)
                            reset_state()

                    # --- Whisper ---
                    elif engine_name == 'whisper':
                        # Принять только ответ на текущую фразу
                        if request_id == current_request_id:
                            current_answers.append(res)
                            process_final_answers(current_answers)
                            reset_state()

            # --- Таймаут Whisper ---
            if vosk_received_at is not None and (perf_counter() - vosk_received_at) > whisper_timeout_sec:
                if current_answers:
                    process_final_answers(current_answers)
                reset_state()

            await asyncio.sleep(0.05)

    consumer_task = asyncio.create_task(consumer())
    await asyncio.to_thread(lambda: input('... press enter for exit ...\n'))
    await engine.stop()
    await engine_task
    await consumer_task


if __name__ == '__main__':
    asyncio.run(main())
