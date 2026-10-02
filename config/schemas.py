from pydantic import BaseModel, ConfigDict, Field
from pathlib import Path
from infrastructure_path_utils import get_root_dir_path

root_dir = get_root_dir_path()


class Settings(BaseModel):
    app_name: str = 'app'
    models_dir: str = 'resources/models'

    @property
    def models_dir_prop(self) -> Path:
        return get_root_dir_path() / self.models_dir

    @property
    def vosk_models_dir_prop(self) -> Path:
        return self.models_dir_prop / 'vosk'

    @property
    def whisper_models_dir_prop(self) -> Path:
        return self.models_dir_prop / 'whisper'


class Parameters(BaseModel):
    samplerate: int = 16000
    blocksize: int = 1024
    model: str = 'vosk-model-small-ru-0.22'
    whisper_model_enable: bool = True
    whisper_model_select: str = Field(default='small')
    model_config = ConfigDict(
        json_schema_extra={
            'examples': [
                {
                    'samplerate': 16000, 'blocksize': 1024, 'model': 'vosk-model-small-ru-0.22',
                    'whisper_model_enable': True, 'whisper_model_select': 'small',
                },
            ]
        }
    )
