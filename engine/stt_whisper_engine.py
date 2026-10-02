import numpy as np
from faster_whisper import WhisperModel, available_models

from config import settings, Parameters


class Engine:
    def __init__(self):
        self._model: WhisperModel | None = None

    @staticmethod
    def is_available_model(model: str):
        return model in available_models()

    def start(self, model: str, samplerate: int):
        # карусель параметров, сверху вниз (можно будет расширить в перспективе)
        start_parameters = [
            {'device': 'cuda', 'compute_type': 'float16'},  # для видеокарт nvidia с драйвером cuda
            {'device': 'cpu', 'compute_type': 'int8'},  # прочее, работа на cpu процессоре
        ]
        for dev in start_parameters:
            self._model = WhisperModel(
                str(settings.models_dir_prop / model),
                # download_root=str(settings.whisper_models_dir_prop),
                local_files_only=True,  # запрет на скачивание моделей без ведома пользователя (политика оффлайн)
                **dev,  # device и compute_type
            )
            try:
                # проверка модели на pcm фрагменте
                self.process(pcm=np.zeros(samplerate // 10, dtype=np.float32))
                dev.update({'model': model})
                print(dev)
                break
            except RuntimeError as err:  # noqa
                # print(f'Не удалось загрузиться на {dev} -> {err}')
                self._model = None
                continue
        if self._model is None:
            raise RuntimeError('Не удалось загрузить stt whisper')

    def process(self, pcm: np.ndarray):
        segments, _ = self._model.transcribe(
            pcm,
            # # встроенный vad, нужно будет поиграться
            # vad_filter=True,
            # vad_parameters={},
        )
        full_text = " ".join(segment.text for segment in segments)
        return full_text.strip()

    def stop(self):
        if self._model is not None:
            del self._model
            self._model = None


if __name__ == '__main__':
    params = Parameters(model='medium')
    # проверка что модель разрешенная
    if Engine.is_available_model(model=params.model):
        eng = Engine()
        eng.start(model='small', samplerate=16000)
