# OsintLost

**OSINT People Search by Photo** — веб-приложение для поиска людей по фотографии.

Локальная детекция лиц (UltraFace), извлечение EXIF/GPS, reverse image search, генерация username-кандидатов и ссылки на профили соцсетей.

> **Этичное использование.** Только публичные данные. Соблюдайте законы и ToS платформ.

![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Возможности

| Модуль | Описание |
|--------|----------|
| **Face Detection** | Локальный UltraFace RFB-320 (ONNX) — bbox + score, annotated-фото |
| **EXIF / GPS** | Камера, дата, ПО, координаты + ссылка на карту |
| **Reverse Image** | Yandex, Google Lens, Bing, TinEye, PimEyes, FaceCheck.ID, Search4Faces, Lenso, FaceSeek, VK Watch |
| **Username gen** | Кандидаты из ФИО (транслит RU→EN) в стиле EagleEye2 |
| **Social links** | Instagram, X, TikTok, VK, Facebook, GitHub, Telegram, YouTube, Reddit, LinkedIn… |
| **OSINT tools** | Готовые команды Sherlock / Maigret, ссылки WhatsMyName, Epieos |

Вдохновлено: [EagleEye2](https://github.com/StefanYasin/eagleeye2), [Sherlock](https://github.com/sherlock-project/sherlock), [Maigret](https://github.com/soxoj/maigret), [awesome-osint](https://github.com/jivoi/awesome-osint).

---

## Быстрый старт

```bash
git clone https://github.com/Alexberik/OsintLost.git
cd OsintLost

# 1. Модель лиц (~1.2 MB)
bash scripts/download_model.sh

# 2. Зависимости
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Запуск
cd backend
PORT=8090 python server.py
```

Открой в браузере: **http://localhost:8090**

Или одной командой:

```bash
bash scripts/run.sh
```

### API

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/` | UI |
| GET | `/api/health` | Статус (Pillow, face detector) |
| POST | `/api/analyze` | `multipart/form-data`: `file`, `name`, `username`, `extra` |
| GET | `/api/report/{job_id}` | JSON-отчёт |
| GET | `/uploads/...` | Загруженные / annotated фото |

Пример:

```bash
curl -s -F "file=@photo.jpg" -F "name=Иван Иванов" http://localhost:8090/api/analyze | jq .
```

---

## Структура

```
OsintLost/
├── backend/
│   ├── server.py          # HTTP-сервер (stdlib + Pillow + onnxruntime)
│   └── face_detector.py   # UltraFace ONNX
├── frontend/
│   └── index.html         # SPA UI (тёмная тема)
├── models/                # version-RFB-320.onnx (скачивается скриптом)
├── scripts/
│   ├── download_model.sh
│   └── run.sh
├── uploads/               # runtime
├── reports/               # JSON-отчёты
├── requirements.txt
└── README.md
```

---

## Зависимости

- Python 3.10+
- `Pillow` — EXIF
- `numpy` + `onnxruntime` — детекция лиц
- Модель: [UltraFace RFB-320](https://github.com/onnx/models/tree/main/validated/vision/body_analysis/ultraface)

Интернет нужен только для скачивания модели и внешних reverse-search ссылок. Сама детекция лиц работает офлайн.

---

## Docker (опционально)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN bash scripts/download_model.sh
ENV PORT=8090
EXPOSE 8090
CMD ["python", "backend/server.py"]
```

```bash
docker build -t osintlost .
docker run -p 8090:8090 osintlost
```

---

## Roadmap

- [x] Локальная детекция лиц (UltraFace)
- [x] EXIF + GPS
- [x] Reverse image / face search links
- [x] Username candidates + social profile links
- [ ] Сохранение кропов лиц
- [ ] Интеграция CLI Sherlock/Maigret из UI
- [ ] Docker Compose + reverse proxy
- [ ] Мультиязычный UI

---

## Disclaimer

Инструмент предназначен для легитимного OSINT, расследований и исследований.  
Автор не несёт ответственности за злоупотребления. Не используйте для преследования, мошенничества или нарушения приватности.

---

## License

MIT
