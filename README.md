# 🗣 STT OFFLINE

**Быстрый оффлайн realtime распознаватель текста**

> Обёртка для работы с моделями распознавания речи из входного аудио [vosk](https://alphacephei.com/vosk/models)
> и [whisper](https://huggingface.co/models?sort=downloads&search=whisper).
> Если ни фига не понятно, то отправьте этот текст в ваш любимый ИИ, ставлю 5 шерифов 🤠🤠🤠🤠🤠 из 5, что он разберется и
> скажет что делать.

---

## Содержание

- [Примечание о безопасности (дисклеймер)](#примечание-о-безопасности-дисклеймер)
- [О проекте](#о-проекте)
- [Системные требования](#системные-требования)
- [Быстрый старт для разработчиков](#быстрый-старт)
- [Связанные репозитории](#связанные-репозитории)
- [Лицензии](#лицензии)
- [Примечания](#примечания)

---

## Примечание о безопасности (Дисклеймер)

Проекты srv-стандарта построены на базе экосистемы Open Source и используют компоненты из разных публичных источников:
библиотеки из репозитория [PyPI](https://pypi.org/), языковые модели с [HuggingFace](https://huggingface.co/), голосовые
движки [Silero](https://silero.ai/), [Vosk](https://alphacephei.com/vosk/) и другие.

Большинство из них распространяются под открытыми лицензиями (MIT, Apache 2.0), но важно учитывать специфику
современного ПО: любой компонент тянет за собой длинную цепочку вложенных зависимостей. Проверить каждый сторонний байт,
модель или скрипт до последнего символа физически невозможно — это классический эффект «черного ящика», характерный для
большинства ИТ-продуктов в мире.

Это не означает, что перечисленные инструменты опасны. Это означает, что **абсолютная гарантия безопасности невозможна**
для любого проекта, использующего внешние библиотеки.

Устанавливая данное приложение, вы принимаете стандартные риски использования Open Source решений. В целях
информационной гигиены любые экспериментальные локальные ИИ-системы рекомендуется запускать в изолированных окружениях
или на рабочих машинах, отдельно от критически важных личных кабинетов и онлайн-банкинга.


---

## О проекте

Микросервис для оффлайн распознавания текста. Самодостаточен, имеет свой аудиорекордер. Может быть интегрирован с
другими сервисами.

**Ключевые особенности:**

- **Реальное время** — подходит для голосовых ассистентов и команд.
- **Не требует мощного GPU** — работает на CPU.
- **Полностью оффлайн** — не лезет в интернет без вашего ведома.
- **Самодостаточен** — запускается как отдельный сервер и интегрируется с другими сервисами.
- **Удобен в использовании** — вы можете спокойно отойти к плите и поправить макароны, пока сервис работает.
- **Интегрировано 2 движка** - whisper дает высокую точность распознавания (от medium+ моделей) но требователен к
  железу, а vosk пойдет даже на слабых машинах и отлично работает как `vad`. Именно из комбинации этих двух движков и
  складывается сервис.

**Основные параметры сервиса:**

- `samplerate` — частота дискретизации (Гц). Определяет, сколько раз в секунду измеряется уровень звука. 16000 Гц —
  стандарт для голосовых команд.
- `pcm` — массив чисел, отражающий отклонение мембраны микрофона от нуля. Например, `[0, -1000, 10, ...]`. Короткий
  всплеск — скорее щелчок, плавные колебания — речь.
- `model` — имя загруженной модели (например, `vosk-model-small-ru-0.22`). Она анализирует PCM и преобразует его в
  текст.

### Что внутри

- **realtime** — рекордер аудио, распознает речь из pcm(значения отклонения мембраны микрофона), и выдает её через
  streaming.
- **REST API** — встраивайте в свои проекты на Python, Go, JavaScript, C# — на любом языке
- **Готовый .exe** — для тех, кто не пишет код. Запустил и работает (после сборки, либо скачивания лаунчером)

---

## Системные требования

- Версия python 3.12.

**Для Windows:**
Может потребоваться пакет **Microsoft Visual C++ Redistributable**. Скачать можно
с [официального сайта Microsoft](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170).

---

## Быстрый старт

> В примерах ниже упоминается подключение к `8000 порту`, порт может быть и любым другим.

### 1. Клонирование

```bash
git clone https://github.com/Mike2024New/srv_stt srv_stt
cd srv_stt
```

### 2. Создать виртуальное окружение

> Важно! Папка с виртуальным окружением должна называться `.venv`

```bash
# Windows
python -m venv .venv && .venv\Scripts\activate

# Linux
python3 -m venv .venv && source .venv/bin/activate
```

### 3. Развернуть проект (установка зависимостей, доп материалов и сборка .exe)

`python start.py all` # автоматически подхватятся все зависимости с которыми работает пакет, а также скачаются модели
распознавания речи vosk ['vosk-model-small-ru-0.22', 'vosk-model-small-en-us-0.15'] и модель распознавания речи
whisper ['small'], скачать дополнительные модели можно [здесь](https://alphacephei.com/vosk/models),
и [здесь](https://huggingface.co/) - вбив в поиск faster-whisper, **распаковать zip
**, за тем положить их по пути: `<корень проекта>/resources/models/whisper` или `<корень проекта>/resources/models/vosk`

### 4. Запустить сервер

`python cli.py run-server -p 8000` - запустится на 8000 порту.

### 5. Запустить движок

<details>
<summary>См. подробный пример.</summary>

```python
import requests

# запуск engine сервиса с передачей параметров. (Метод идемпотентен)
requests.post(
    url=f'http://localhost:8000/start/',
    json={
        'samplerate': 16000,  # частота замеров в секунду звуковой волны (дискретизация в ГЦ)
        'blocksize': 1024,  # размер одного блока данных
        'model': 'vosk-model-small-ru-0.22',  # модель семейства vosk для распознавания речи
        'whisper_model_enable': True, 'whisper_model_select': 'small',  # подключение whisper
    },
)

# Опционально: проверка что engine запущен
response = requests.get(url='http://localhost:8000/parameters/')
assert response.status_code == 200
parameters = response.json()
assert parameters.get('parameters', {})
assert parameters.get('running') is True
```

</details>

> Модель распознавания речи загружена в память.

### 6. Просмотр списка доступных моделей

<details>
<summary>См. подробный пример.</summary>

```python

import requests

url = 'http://localhost:8000/models/'

response = requests.get(url)
assert response.json()  # например {'models_list': ['vosk-model-small-en-us-0.15', 'vosk-model-small-ru-0.22']}

```

</details>

### 7. Использовать стриминг ws, для получения распознанного аудио.

<details>
<summary>См. подробный пример.</summary>

```python
import json
import websockets, asyncio


# клиент потребитель распознанного аудио. Если есть текст он высылает, если нет, молчит.

async def main():
    async with websockets.connect('ws://localhost:8000/ws') as ws:  # установка соединения
        event = asyncio.Event()  # флаг выхода
        try:
            async def consumer():
                while not event.is_set():
                    try:
                        # во избежание зависания стриминга желательно использовать wait_for
                        data = await asyncio.wait_for(ws.recv(), timeout=0.1)
                        data = json.loads(data)  # пример: {'type': 'result', 'text': 'распознанный текст'}
                        print(data)  # обработка полученной фразы
                    except asyncio.TimeoutError:
                        pass

            task = asyncio.create_task(consumer())
            await asyncio.to_thread(lambda: input('...press enter for exit...\n'))
            event.set()
            await task

        except websockets.exceptions.ConnectionClosedOK:
            event.set()  # соединение закрыто штатно, всё в порядке, не логировать

        except Exception as err:  # обработка ошибки, логировать
            print(f'Ошибка соединения {err}')
            event.set()


if __name__ == '__main__':
    asyncio.run(main())

```

</details>

### 8. Остановка сервиса.

#### Корректная остановка сервиса:

- выплонить get запрос `http://localhost:8000/stop/`
- выплонить get запрос `http://localhost:8000/shutdown/`

> Произойдет полная остановка текущего сервиса, и запущенного внутри стриминга, память будет высвобождена.

### 9. Собрать exe/bin из лаунчера (если планируется работать не из кода)

`python cli.py build -oe` - oe соберет приложение одним файлом. Путь покажет в консольном выводе.

> см. подробнее справку в `python cli.py --help`

### 10. Полный рабочий пример с запуском, полезной нагрузкой и остановкой движка

Продублирован в  [example.py](example.py), чтобы запустить его выполнить `python example.py`

<details>

<summary>См. подробный пример</summary>

```python

import asyncio, subprocess, aiohttp, websockets, json, sys
from pathlib import Path
from infrastructure_http_clients import ServerProbe

port = 8000


async def run_server() -> subprocess.Popen:
    # 1.запустить сервер
    cmd = [sys.executable, 'cli.py', 'run-server', '--port', str(port), '--log-level', 'info']
    process = subprocess.Popen(cmd, cwd=Path.cwd())

    # 2. Ожидание запуска сервера (пока сервер не станет отвечать на /health/, например torch загружается долго)
    print(f'Ожидание запуска сервера')
    ServerProbe.wait_for_server_up(
        url=f'http://127.0.0.1:{port}/health/',
        timeout=30,
        expected_status=200,
    )

    # 3. Запуск engine, с переданными параметрами модели
    async with aiohttp.ClientSession() as session:
        parameters = {
            'samplerate': 16000, 'blocksize': 1024, 'model': 'vosk-model-small-ru-0.22',
            'whisper_model_enable': True, 'whisper_model_select': 'small',  # подключение whisper
        }
        print(f'Запуск engine сервера')
        async with session.post(url=f'http://127.0.0.1:{port}/start/', json=parameters) as resp:
            answer = await resp.json()
            print(answer)
            assert resp.status == 200, f'Engine сервера не был запущен.'
    return process


async def example():
    """
    Подключение к сокету и получение данных реал-тайм
    """
    async with websockets.connect(f'ws://127.0.0.1:{port}/ws') as ws:  # установка соединения
        event = asyncio.Event()  # флаг выхода
        try:
            async def consumer():
                while not event.is_set():
                    try:
                        # во избежание зависания стриминга желательно использовать wait_for
                        data = await asyncio.wait_for(ws.recv(), timeout=0.1)
                        data = json.loads(data)  # пример: {'type': 'result', 'text': 'распознанный текст'}
                        print(data)  # обработка полученной фразы
                    except asyncio.TimeoutError:
                        pass

            task = asyncio.create_task(consumer())
            print(f'Говорите, что нибудь, через 10 секунд компонент отключится.')
            await asyncio.sleep(10)
            event.set()
            await task

        except websockets.exceptions.ConnectionClosedOK:
            event.set()  # соединение закрыто штатно, всё в порядке, не логировать

        except Exception as err:  # обработка ошибки, логировать
            print(f'Ошибка соединения {err}')
            event.set()


async def graceful_shutdown(process: subprocess.Popen):
    """Аккуратная остановка сервера"""
    async with aiohttp.ClientSession() as session:
        # остановить engine сервера (высвобождение памяти)
        print(f'Остановка engine сервера')
        async with session.get(url=f'http://127.0.0.1:{port}/stop/') as resp:
            assert resp.status == 200, f'Engine сервера не был остановлен.'
        # остановить сервер
        print(f'Остановка сервера')
        async with session.get(url=f'http://127.0.0.1:{port}/shutdown/') as resp:
            assert resp.status == 200, f'Сервер не был остановлен.'

    # 5. Убедиться что процесс завершился
    process.wait(timeout=10)


async def main():
    process = await run_server()  # запуск сервера и движка
    await example()  # пример взаимодействия с сервером (получение распознанного текста реал-тайм)
    await graceful_shutdown(process=process)  # аккуратная остановка сервера


if __name__ == '__main__':
    asyncio.run(main())



```

</details>

---

## Связанные репозитории

- [infrastructure2](https://github.com/Mike2024New/infrastructure2) — набор утилит (сервер, логи, сборка)

---

## Лицензии

* Этот проект распространяется под лицензией MIT. Подробнее в файле [LICENSE](LICENSE).
* Модели Vosk, скачиваемые стартовым скриптом ['vosk-model-small-en-us-0.15', 'vosk-model-small-ru-0.22'] и
  использующиеся в сервисе, распространяются под лицензией Apache 2.0.
  См. [источник](https://alphacephei.com/vosk/models).
* Модели **Whsiper** скачиваемые стартовым скриптом, распространяются под лицензией Apache-2.0.
  См. [источник](https://huggingface.co/models?sort=downloads&search=whisper).

---

## Примечания

- Список моделей можно расширить: нужно скачать [модели](https://alphacephei.com/vosk/models), распаковать zip и
  разместить их по пути - <корневая папка приложения>/resources/models
- Сервисы, построенные на базе этого шаблона предназначены для desktop приложений (не web), но можно например
  скомпилировав .bin развернуть приложение на сервере и управлять им дергая его через api локальной сети через внешний
  оркестратор.
- Проект использует утилиты из репозитория [infrastructure2](https://github.com/Mike2024New/infrastructure2).

> Если ни фига не понятно, то отправьте этот текст в ваш любимый ИИ, ставлю 5 шерифов 🤠🤠🤠🤠🤠 из 5, что он разберется и
> скажет что делать.

> Не силен в грамматике, мог забыть где-то поставить запятые, поэтому ставлю их здесь (,,,,,,,,,,,,,,,,,,,,,,,), с
> запасом.