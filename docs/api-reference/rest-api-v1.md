# REST API v1 Contract

The lightweight SousChef REST API provides deterministic HTTP access to key migration workflows.

## Base URL

- Local default: `http://127.0.0.1:8081`
- Content type: `application/json`

## Endpoint Summary

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/operations` | List generic operation names exposed by `/api/v1/run` |
| `POST` | `/api/v1/run` | Execute a named operation with arguments |
| `POST` | `/api/v1/migration/analyse` | Assess migration complexity |
| `POST` | `/api/v1/migration/plan` | Generate migration plan |
| `POST` | `/api/v1/migration/generate-playbook` | Generate playbook from Chef recipe |
| `POST` | `/api/v1/validation/profile` | Validate conversion output using profile filtering |
| `POST` | `/api/v1/context/query` | Query capability context with optional cookbook enrichment |
| `POST` | `/api/v1/webhooks/notify` | Send webhook notification |

## Request/Response Contracts

### `POST /api/v1/migration/analyse`

Request schema:

```json
{
  "cookbook_paths": ["/abs/path/to/cookbook"],
  "migration_scope": "full",
  "target_platform": "ansible_awx"
}
```

- `cookbook_paths`: `string | string[]` (required, non-empty)
- `migration_scope`: `string` (optional, default: `full`)
- `target_platform`: `string` (optional, default: `ansible_awx`)

Success schema:

```json
{
  "status": "success",
  "operation": "assess_chef_migration_complexity",
  "result": "<markdown report>"
}
```

### `POST /api/v1/migration/plan`

Request schema:

```json
{
  "cookbook_paths": ["/abs/path/to/cookbook"],
  "migration_strategy": "phased",
  "timeline_weeks": 12
}
```

- `cookbook_paths`: `string | string[]` (required, non-empty)
- `migration_strategy`: `string` (optional, default: `phased`)
- `timeline_weeks`: `integer` (optional, default: `12`, minimum: `1`)

Success schema:

```json
{
  "status": "success",
  "operation": "generate_migration_plan",
  "result": "<markdown plan>"
}
```

### `POST /api/v1/migration/generate-playbook`

Request schema:

```json
{
  "recipe_path": "/abs/path/to/recipe.rb",
  "cookbook_path": "/abs/path/to/cookbook"
}
```

- `recipe_path`: `string` (required, non-empty)
- `cookbook_path`: `string` (optional)

Success schema:

```json
{
  "status": "success",
  "operation": "generate_playbook_from_recipe",
  "result": "<yaml playbook>"
}
```

### `POST /api/v1/validation/profile`

Request schema:

```json
{
  "conversion_type": "recipe",
  "result_content": "- hosts: all\n  tasks: []",
  "validation_profile": "moderate"
}
```

- `conversion_type`: `string` (required)
- `result_content`: `string` (required)
- `validation_profile`: `string` (optional, default: `moderate`)

Supported profiles:

- `basic`
- `moderate`
- `safety`
- `shared`
- `production`

Success schema:

```json
{
  "status": "success",
  "operation": "validate_conversion_with_profile",
  "profile": "moderate",
  "conversion_type": "recipe",
  "passed": true,
  "summary": {
    "total_checks": 8,
    "errors": 0,
    "warnings": 1,
    "infos": 2,
    "pass_rate": 87.5
  },
  "result_count": 3,
  "results": [
    {
      "level": "warning",
      "category": "best_practice",
      "message": "Example"
    }
  ]
}
```

### `POST /api/v1/context/query`

Request schema:

```json
{
  "query": "migration plan timeline",
  "top_k": 5,
  "cookbook_path": "/abs/path/to/cookbook"
}
```

- `query`: `string` (required, must contain alphanumeric tokens)
- `top_k`: `integer` (optional, default: `5`, range: `1..20`)
- `cookbook_path`: `string` (optional, must resolve to a directory within workspace boundary)

Success schema:

```json
{
  "status": "success",
  "operation": "context_query",
  "query": "migration plan timeline",
  "top_k": 5,
  "cookbook_path": "/abs/path/to/cookbook",
  "match_count": 2,
  "matches": [
    {
      "score": 3,
      "id": "endpoint.migration.plan",
      "kind": "endpoint",
      "title": "Migration planning",
      "description": "Generate a phased or parallel migration plan with timeline.",
      "route": "/api/v1/migration/plan"
    }
  ]
}
```

### `POST /api/v1/webhooks/notify`

Request schema:

```json
{
  "url": "https://hooks.example.test/notify",
  "event": "migration.completed",
  "payload": {
    "status": "ok"
  },
  "secret": "optional-signing-secret"
}
```

- `url`: `string` (required)
- `event`: `string` (required)
- `payload`: `object` (required)
- `secret`: `string` (optional)

Success schema:

```json
{
  "status": "success",
  "status_code": 200
}
```

## Error Contract

Error responses use JSON with an `error` field.

```json
{
  "error": "Human-readable validation or execution message"
}
```

Common status codes:

- `400` invalid request payload or argument validation failures
- `404` unknown route or unknown operation name
- `502` upstream runtime failures (for operation execution or webhook delivery)

## Versioning And Compatibility Policy

- API major version is encoded in path (`/api/v1/...`).
- Backward-compatible additions in v1 are allowed:
  - adding new endpoints
  - adding optional request fields
  - adding optional response fields
- Breaking changes require a new major version path (`/api/v2/...`), including:
  - removing or renaming endpoints
  - changing required fields
  - changing response field meaning or type
  - tightening validation in a way that rejects previously valid requests
- Existing v1 behaviour remains supported for at least one minor release after v2 is introduced.
- Deprecations must be documented in release notes and in this reference.
