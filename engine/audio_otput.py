import queue
import soxr
import numpy as np
import pyaudiowpatch as pyaudio
from queue import Queue


class Engine:
    def __init__(self):
        self._running = False
        self._pyaudio: pyaudio.PyAudio | None = None
        self._stream_loopback = None
        self.queue: Queue[np.ndarray] = Queue(maxsize=200)
        self._info_loopback = None
        self.samplerate = 16000
        self.channels = 1
        self._resampler: soxr.ResampleStream | None = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._pyaudio = pyaudio.PyAudio()
        # поиск loopback устройства (выхода аудио)
        try:
            self._info_loopback = self._pyaudio.get_default_wasapi_loopback()
        except OSError:
            self._pyaudio.terminate()
            raise RuntimeError(f'loopback устройство не найдено')

        self.samplerate = int(self._info_loopback['defaultSampleRate'])
        self.channels = int(self._info_loopback['maxInputChannels'])

        self._resampler = soxr.ResampleStream(
            self.samplerate,
            out_rate=16000,
            num_channels=1,
            dtype='float32',
        )

        self._stream_loopback = self._pyaudio.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.samplerate,
            input=True,
            input_device_index=self._info_loopback['index'],
            stream_callback=self._callback,
        )

    def _callback(self, in_data, _frame_count, _time_info, _status):
        """Получение выходного аудио с колонок, вызывается только если есть звук на колонки, иначе простаивает"""
        if not self._running:
            return None, pyaudio.paContinue
        if in_data:
            pcm = np.frombuffer(in_data, dtype=np.int16).reshape(-1, self.channels)
            pcm_mono = pcm.mean(axis=1).astype(np.float32) / 32768.0  # перевод в моно
            print(f"pcm: {pcm}")
            print(f"pcm_mono: {pcm_mono}")
            if len(pcm_mono) > 0:  # отсечка пустых чанков
                # ресемплировать в 16000
                audio_output_pcm = self._resampler.resample_chunk(pcm_mono, last=False)
                try:
                    self.queue.put(audio_output_pcm, block=False)
                except queue.Full:
                    self.queue.get_nowait()
                    self.queue.put(audio_output_pcm, block=False)
        return None, pyaudio.paContinue

    def stop(self):
        if not self._running:
            return
        self._running = False
        self._stream_loopback.stop_stream()
        self._stream_loopback.close()
        self._pyaudio.terminate()
        self._pyaudio = None
        self._stream_loopback = None
        self._info_loopback = None
        self._resampler = None


if __name__ == '__main__':
    eng = Engine()
    eng.start()
    input('...')
    eng.stop()
