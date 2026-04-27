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
    "groupable": true,
    "filterable": true,
    "aggregations": []
  },
  {
    "id": "student_count",
    "label": "Количество",
    "type": "number",
    "groupable": false,
    "filterable": false,
    "aggregations": ["count"]
  }
]
```

Frontend rules:

- fields with `groupable=true` can be used in `dimensions`;
- fields with non-empty `aggregations` can be used in `metrics`;
- fields with `filterable=true` can be used in `filters`.

## Analytics Query

### `POST /analytics/query`

Request:

```json
{
  "metrics": [
    { "field": "student_count", "aggregation": "count" }
  ],
  "dimensions": ["military_specialty"],
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
    { "key": "military_specialty", "label": "ВУС", "type": "string" },
    { "key": "student_count", "label": "Количество", "type": "number" }
  ],
  "rows": [
    { "military_specialty": "Оператор БПЛА", "student_count": 12 }
  ]
}
```

Frontend can render `columns` as table headers and `rows` as table data. For charts, usually one dimension becomes the X axis and the first metric becomes the Y value.

## Query Limits

- `metrics`: 0-2 items;
- `dimensions`: 0-2 items;
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
