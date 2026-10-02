import json
from vosk import Model, KaldiRecognizer
from infrastructure_other import ShutUpLogs
from config import settings


class Engine:
    def __init__(self):
        self._model = None
        self._recognizer = None
        self._shut_up = ShutUpLogs()

    def start(self, model: str, samplerate: int):
        self._shut_up.enable()  # успокоить логи vosk

        # vosk в этом проекте грузится всегда даже если он не используется как stt(он нужен как vad)
        if not (settings.models_dir_prop / model).exists():
            raise RuntimeError(f'Отсутствует дефолтная модель `{model}`')

        self._model = Model(str(settings.models_dir_prop / model))
        self._recognizer = KaldiRecognizer(self._model, samplerate)
        self._shut_up.disable()

    def recognized(self, chunk):
        """Может использоваться как callback"""
        if self._recognizer.AcceptWaveform(chunk):
            result = json.loads(self._recognizer.Result())
            text = result.get('text', '')
            if text:
                return {'type': 'result', 'text': text, 'engine': 'vosk'}
        else:
            partial = json.loads(self._recognizer.PartialResult())
            partial_text = partial.get('partial', '')
            if partial_text:
                return {'type': 'partial', 'text': partial_text, 'engine': 'vosk'}
        return {'type': 'null', 'text': '', 'engine': 'vosk'}

    def stop(self):
        if self._model is not None:
            del self._model
            del self._recognizer
            self._model = None
            self._recognizer = None
