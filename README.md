# Document Search Service

[![CI](https://github.com/MagNat521/document-search-service/actions/workflows/ci.yml/badge.svg)](https://github.com/MagNat521/document-search-service/actions/workflows/ci.yml)

Простой поисковик по текстам документов.

* **Хранилище** — PostgreSQL (поля документа: `id`, `rubrics`, `text`, `created_date`).
* **Поисковый индекс** — Elasticsearch (поля `id` + `text`).
* **API** — FastAPI, полностью асинхронный.

Сервис умеет:

1. принимать произвольный текстовый запрос, искать по тексту документа в индексе и
   возвращать первые 20 документов со всеми полями БД, упорядоченные по дате создания;
2. удалять документ из БД и индекса по `id`.

## Стек

| Компонент         | Технология                                   |
|-------------------|----------------------------------------------|
| Веб-фреймворк     | FastAPI (ASGI, async)                         |
| БД                | PostgreSQL 16 + SQLAlchemy 2.0 (asyncpg)      |
| Поиск             | Elasticsearch 8 (async-клиент)               |
| Запуск            | Docker / docker compose                       |
| Тесты             | pytest + pytest-asyncio + httpx               |

Все вызовы к БД и Elasticsearch — асинхронные.

## Структура проекта

```
.
├── app/
│   ├── main.py            # сборка FastAPI-приложения, lifespan
│   ├── config.py          # настройки (env)
│   ├── db.py              # async-движок SQLAlchemy, сессии
│   ├── models.py          # ORM-модель Document
│   ├── schemas.py         # Pydantic-схемы запросов/ответов
│   ├── search.py          # клиент и операции Elasticsearch
│   ├── service.py         # бизнес-логика (синхронизация БД и индекса)
│   └── routers/documents.py  # HTTP-эндпоинты
├── scripts/
│   ├── ingest.py          # загрузка CSV в БД и индекс
│   └── export_openapi.py  # генерация docs.json
├── tests/                 # функциональные тесты
├── data/posts.csv         # тестовый массив данных (1500 документов)
├── docker-compose.yml
├── Dockerfile
├── docs.json              # OpenAPI-документация сервиса
└── README.md
```

## Как устроен поиск

Индекс по условию задачи хранит только `id` и `text`, поэтому сортировка по дате
делается в БД:

1. Elasticsearch по запросу (`match` по полю `text`) возвращает id подходящих
   документов, ранжированные по релевантности (до `SEARCH_CANDIDATE_POOL` штук).
2. PostgreSQL загружает эти документы и сортирует их по `created_date`
   (по умолчанию — новые сверху), возвращая первые `SEARCH_RESULT_SIZE` (20).

## Быстрый старт (Docker)

Нужен установленный Docker с docker compose.

```bash
docker compose up -d --build
```

Поднимутся четыре сервиса:

* `db` — PostgreSQL;
* `elasticsearch` — Elasticsearch (single-node, без security);
* `app` — API на порту **8000**;
* `ingest` — разовая задача: загружает `data/posts.csv` в БД и индекс, затем завершается
  (идемпотентна — повторный запуск не дублирует данные).

Проверка, что всё поднялось:

```bash
curl http://localhost:8000/health
```

Интерактивная документация (Swagger UI) — <http://localhost:8000/docs>.

### Примеры запросов

Поиск (первые 20 документов, новые сверху):

```bash
curl "http://localhost:8000/documents/search?query=скин"
```

Поиск с сортировкой по возрастанию даты:

```bash
curl "http://localhost:8000/documents/search?query=скин&order=asc"
```

Удаление документа по `id`:

```bash
curl -X DELETE http://localhost:8000/documents/42
```

Создание документа (вспомогательный метод):

```bash
curl -X POST http://localhost:8000/documents \
  -H "Content-Type: application/json" \
  -d '{"text":"пример текста","rubrics":["VK-1"],"created_date":"2020-01-01T10:00:00"}'
```

Перезагрузить данные с нуля:

```bash
docker compose run --rm ingest python -m scripts.ingest --csv data/posts.csv --recreate
```

Остановить и удалить всё (вместе с данными):

```bash
docker compose down -v
```

## Запуск без Docker (локально)

Нужны запущенные PostgreSQL и Elasticsearch 8 (например, свои локальные инстансы).

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt

# настройте подключение (или используйте значения по умолчанию)
cp .env.example .env

# загрузка данных
python -m scripts.ingest --csv data/posts.csv

# запуск сервиса
uvicorn app.main:app --reload
```

Переменные окружения (см. `.env.example`): `DATABASE_URL`, `ELASTICSEARCH_URL`,
`ELASTICSEARCH_INDEX`, `SEARCH_RESULT_SIZE`, `SEARCH_CANDIDATE_POOL`.

При старте приложение само создаёт таблицы и индекс (ждёт, пока БД и ES станут
доступны), так что отдельная миграция не требуется.

## API

| Метод  | Путь                      | Описание                                                        |
|--------|---------------------------|-----------------------------------------------------------------|
| GET    | `/documents/search`       | Поиск по тексту; `query` (обяз.), `order` = `desc`/`asc`.       |
| DELETE | `/documents/{id}`         | Удалить документ из БД и индекса. `204` / `404`.                |
| POST   | `/documents`              | Создать документ (вспомогательный). `201`.                      |
| GET    | `/documents/{id}`         | Получить документ по `id` (вспомогательный). `200` / `404`.     |
| GET    | `/health`                 | Проверка живости.                                               |

Основные по заданию — первые два; остальные добавлены для удобства и тестов.

Полная спецификация — в [`docs.json`](docs.json) (OpenAPI 3.1). Её же в браузере:
`/docs` (Swagger UI) и `/redoc`.

Пересобрать `docs.json`:

```bash
python -m scripts.export_openapi
```

## Тесты

Функциональные тесты поднимают реальное приложение (httpx ASGI) поверх реальных
PostgreSQL и Elasticsearch. Они изолированы: используют отдельную БД `<db>_test` и
индекс `documents_test`, которые пересоздаются на каждый тест, — рабочие данные не
затрагиваются.

Поднимите зависимости и запустите pytest:

```bash
docker compose up -d db elasticsearch
pip install -r requirements-dev.txt
pytest
```

Покрываются: healthcheck, создание/получение, валидация пустого запроса,
поиск с сортировкой по дате (desc/asc), ограничение в 20 результатов и удаление
документа из БД и индекса.

Эти же тесты автоматически прогоняются в CI (GitHub Actions) против реальных
PostgreSQL и Elasticsearch — см. [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Детали реализации

* **id генерируются при загрузке** — в исходном CSV колонки `id` нет; id присваивает
  БД и затем он же используется как `_id` в Elasticsearch, чтобы хранилища были
  согласованы.
* **`rubrics`** в CSV записаны как строковый python-литерал списка
  (`"['VK-1', 'VK-2']"`) и разбираются через `ast.literal_eval`.
* **Near-real-time**: Elasticsearch делает новые документы доступными для поиска после
  refresh (~1 c). При массовой загрузке и в тестах refresh вызывается явно.
* В продакшене вместо `create_all` стоило бы использовать миграции (Alembic), а
  запись в два хранилища защитить outbox-паттерном; здесь для простоты это опущено.
