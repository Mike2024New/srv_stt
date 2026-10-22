import numpy as np
from faster_whisper import WhisperModel, available_models

from config import settings, logger


class Engine:
    def __init__(self):
        self._model: WhisperModel | None = None
        self._model_name: str | None = None
        self._samplerate: int | None = None
        self._device_parameters: dict | None = None

    @staticmethod
    def is_available_model(model: str):
        return model in available_models()

    def start(self, model: str, samplerate: int):
        self._model_name = model
        self._samplerate = samplerate
        # карусель параметров, сверху вниз (можно будет расширить в перспективе)
        start_parameters = [
            {'device': 'cuda', 'compute_type': 'float16'},  # для видеокарт nvidia с драйвером cuda
            {'device': 'cpu', 'compute_type': 'int8'},  # прочее, работа на cpu процессоре
        ]
        for dev in start_parameters:
            self._model = WhisperModel(
                str(settings.models_dir_prop / model),
                local_files_only=True,  # запрет на скачивание моделей без ведома пользователя (политика оффлайн)
                **dev,  # device и compute_type
            )
            try:
                # проверка модели на pcm фрагменте
                self._device_parameters = dev
                self.process(pcm=np.zeros(samplerate // 10, dtype=np.float32))
                dev.update({'model': model})
                logger.debug(f'Включен stt whisper {dev}')
                break
            except RuntimeError as err:  # noqa
                # print(f'Не удалось загрузиться на {dev} -> {err}')
                self._model = None
                continue
        if self._model is None:
            raise RuntimeError('Не удалось загрузить stt whisper')

    def _reset_model(self):
        """Иногда бывают проблемы с cublas (устаревший драйвер, и whisper инициализируется на cuda проходя тест,
        но падает на первой транскрибации, этот метод сбрасывает на cpu)"""
        if self._model_name is None:
            logger.error('Модель не была реинициализированна, так как пустой model_name')
            raise RuntimeError('Модель не была реинициализированна, так как пустой model_name')
        self._device_parameters = {'device': 'cpu', 'compute_type': 'int8'}
        logger.error(f'Реинициализация модели на cpu')
        self._model = WhisperModel(
            str(settings.models_dir_prop / self._model_name),
            local_files_only=True,  # запрет на скачивание моделей без ведома пользователя (политика оффлайн)
            **self._device_parameters,
        )

    def _transcribe(self, pcm: np.ndarray):
        segments, _ = self._model.transcribe(
            pcm,
            language='ru',  # предпочитаемый язык (потом вынести это в параметры, если в планах будет сделать др. языки)
            vad_filter=True,  # встроенный vad, дополнительная чистка от лишнего шума и тишины
            vad_parameters={
                'min_silence_duration_ms': 500
            },  # конфигурирование vad, потом вынести в конфиг
        )
        full_text = " ".join(segment.text for segment in segments)
        return full_text.strip()

    def process(self, pcm: np.ndarray):
        try:
            return self._transcribe(pcm=pcm)
        except Exception as err:
            logger.error(f'Ошибка транскрибации, попытка реинициализировать модель, текст ошибки: {err}')
            self._reset_model()  # попытка перезагрузить модель
            try:
                return self._transcribe(pcm=pcm)
            except Exception as err2:
                logger.exception(f'Повторная ошибка транскрибации, реинициализация на CPU не помогла: {err2}')
                raise

    def stop(self):
        if self._model is not None:
            del self._model
            self._model = None


if __name__ == '__main__':
    print(available_models())
