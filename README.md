# vkr-analysis

Backend MVP аналитического модуля ВУЦ. Приложение строится как FastAPI API поверх существующей PostgreSQL-БД и использует семантический слой, чтобы frontend работал с аналитическими полями, а не с физическими колонками БД.

## Стек

- FastAPI
- SQLModel / SQLAlchemy
- PostgreSQL
- JWT auth
- pytest
- uv

## Запуск

1. Установить зависимости:

```bash
uv sync
```

2. Создать `.env` по примеру `.env.example` и указать подключение к БД:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/vkr
JWT_SECRET_KEY=change-me
```

3. Запустить backend:

```bash
uv run uvicorn app.main:app --reload
```

API будет доступно на `http://127.0.0.1:8000`.

## Основные endpoints

- `GET /health` - проверка состояния API.
- `POST /auth/login` - получение bearer token.
- `GET /auth/me` - текущий пользователь.
- `GET /analytics/fields` - доступный каталог аналитических полей.
- `POST /analytics/query` - выполнение аналитического запроса.

## Пример аналитического запроса

```json
{
  "metrics": [{ "field": "student_count", "aggregation": "count" }],
  "dimensions": ["military_specialty"],
  "filters": [
    { "field": "medical_result", "operator": "in", "value": ["А", "Б"] }
  ],
  "sort": [{ "field": "student_count", "direction": "desc" }],
  "limit": 100
}
```

## Тесты

```bash
uv run pytest
```