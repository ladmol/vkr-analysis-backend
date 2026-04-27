# Frontend API Contract

Backend base URL for local development:

```text
http://127.0.0.1:8000
```

## Auth

### `POST /auth/login`

Request:

```json
{
  "login": "admin",
  "password": "admin"
}
```

Response:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

Frontend stores `access_token` and sends it to protected endpoints:

```http
Authorization: Bearer <jwt>
```

### `GET /auth/me`

Response:

```json
{
  "id": 1,
  "login": "admin",
  "role": "admin"
}
```

Roles:

- `admin`;
- `operator`;
- `observer`.

## Analytics Fields

### `GET /analytics/fields`

Returns fields available to the current role.

Response:

```json
[
  {
    "id": "military_specialty",
    "label": "ВУС",
    "type": "string",
    "displayable": true,
    "groupable": true,
    "filterable": true,
    "aggregations": []
  },
  {
    "id": "student_count",
    "label": "Количество",
    "type": "number",
    "displayable": false,
    "groupable": false,
    "filterable": false,
    "aggregations": ["count"]
  }
]
```

Frontend rules:

- fields with `groupable=true` can be used in `dimensions`;
- fields with `displayable=true` can be used in detail `columns`;
- fields with non-empty `aggregations` can be used in `metrics`;
- fields with `filterable=true` can be used in `filters`.

## Analytics Summary Query

### `POST /analytics/summary`

Request:

```json
{
  "metrics": [
    { "field": "student_count", "aggregation": "count" }
  ],
  "dimensions": ["platoon", "military_commissariat"],
  "filters": [
    { "field": "status", "operator": "eq", "value": "ENROLLED" }
  ],
  "sort": [
    { "field": "student_count", "direction": "desc" }
  ],
  "limit": 100
}
```

Response:

```json
{
  "columns": [
    { "key": "platoon", "label": "Взвод", "type": "string" },
    { "key": "military_commissariat", "label": "Военный комиссариат", "type": "string" },
    { "key": "student_count", "label": "Количество", "type": "number" }
  ],
  "rows": [
    { "platoon": "1 взвод", "military_commissariat": "Ярославский ОВК", "student_count": 12 }
  ]
}
```

Frontend can render `columns` as table headers and `rows` as table data. For charts, usually one dimension becomes the X axis and the first metric becomes the Y value.

`POST /analytics/query` remains as a compatibility alias for summary requests.

### `POST /analytics/summary/export/xlsx`

Accepts the same request body as `POST /analytics/summary`.

Response:

```text
application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
```

Frontend should download the response as `summary-report.xlsx`.

`POST /analytics/query/export/xlsx` remains as a compatibility alias.

## Analytics Detail Query

### `POST /analytics/detail`

Request:

```json
{
  "columns": [
    "full_name",
    "platoon",
    "military_commissariat",
    "military_specialty",
    "final_result"
  ],
  "filters": [
    { "field": "platoon", "operator": "eq", "value": "1 взвод" }
  ],
  "sort": [
    { "field": "final_result", "direction": "desc" }
  ],
  "limit": 100
}
```

Response:

```json
{
  "columns": [
    { "key": "full_name", "label": "ФИО", "type": "string" },
    { "key": "platoon", "label": "Взвод", "type": "string" },
    { "key": "military_commissariat", "label": "Военный комиссариат", "type": "string" },
    { "key": "military_specialty", "label": "ВУС", "type": "string" },
    { "key": "final_result", "label": "Итоговый балл", "type": "number" }
  ],
  "rows": [
    {
      "full_name": "Иванов Иван Иванович",
      "platoon": "1 взвод",
      "military_commissariat": "Ярославский ОВК",
      "military_specialty": "Оператор БПЛА",
      "final_result": 176
    }
  ]
}
```

Detail mode is intended for row-level lists and XLSX exports. The frontend still sends only catalog field ids, never SQL or physical database column names.

### `POST /analytics/detail/export/xlsx`

Accepts the same request body as `POST /analytics/detail` and returns XLSX.

## Rating

### `POST /analytics/rating`

Request:

```json
{
  "status": "ENROLLED",
  "military_specialty": "Оператор БПЛА",
  "study_group": "ЦИС-21",
  "fitness_category": "А",
  "psycho_category": "I",
  "limit": 100
}
```

All filters are optional.

Response:

```json
{
  "rows": [
    {
      "full_name": "Иванов Иван Иванович",
      "study_group": "ЦИС-21",
      "military_specialty": "Оператор БПЛА",
      "status": "ENROLLED",
      "fitness_category": "А",
      "psycho_category": "I",
      "grade100": 82.5,
      "total_points": 154,
      "final_result": 176
    }
  ]
}
```

Rows are sorted by `final_result desc`. For `observer`, sensitive personal fields such as `full_name` may be hidden.

### `POST /analytics/rating/export/xlsx`

Accepts the same request body as `POST /analytics/rating` and returns XLSX.

## Query Limits

- `metrics`: 0-3 items;
- `dimensions`: 0-3 items;
- `detail columns`: 1-16 items;
- `sort`: 0-3 items;
- `limit`: 1-500.

At least one metric or one dimension is required.

## Operators

- `eq` - exact equality;
- `in` - value is inside a list;
- `gte` - greater than or equal, for numeric/date fields;
- `lte` - less than or equal, for numeric/date fields;
- `contains` - substring match, only for string fields.

## Errors

Expected error shape from FastAPI:

```json
{
  "detail": "Field cannot be filtered: student_count"
}
```

Frontend should show `detail` as a user-facing error for validation problems.
