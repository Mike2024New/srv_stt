import numpy as np
from faster_whisper import WhisperModel

from config import settings, Parameters


class Engine:
    def __init__(self):
        self._model: WhisperModel | None = None

    def start(self, parameters: Parameters):
        # карусель параметров, сверху вниз (можно будет расширить в перспективе)
        start_parameters = [
            {'device': 'cuda', 'compute_type': 'float16'},  # для видеокарт nvidia с драйвером cuda
            {'device': 'cpu', 'compute_type': 'int8'},  # прочее, работа на cpu процессоре
        ]
        for dev in start_parameters:
            self._model = WhisperModel(
                str(settings.whisper_models_dir_prop / parameters.whisper_model_select),
                # download_root=str(settings.whisper_models_dir_prop),
                local_files_only=True,  # запрет на скачивание моделей без ведома пользователя (политика оффлайн)
                **dev,
            )
            try:
                # проверка модели на pcm фрагменте
                self.process(pcm=np.zeros(16000 // 10, dtype=np.float32))
                dev.update({'model': parameters.whisper_model_select})
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
    eng = Engine()
    eng.start(parameters=Parameters(whisper_model_select='medium'))
