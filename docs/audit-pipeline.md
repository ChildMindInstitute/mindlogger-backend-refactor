## What gets logged

Every audit event is an `AuditEvent` object (`apps/audit/domain.py`). It captures:

| Group | Fields | Example |
|---|---|---|
| **What happened** | `event_action`, `event_outcome` | `user:session:login`, `success` |
| **Who did it** | `user_id`, `user_roles` | the logged-in user's UUID and roles |
| **Who was affected** | `user_target_id`, `user_target_email` | for IAM events (role changes, invites, etc.) |
| **How** | `client_ip`, `http_request_method`, `url_path`, `http_response_status_code` | the HTTP request that triggered it |
| **What data was touched** | `curious_applet_id`, `curious_subject_id`, `curious_answer_id`, ... | Curious record IDs |
| **Context** | `@timestamp`, `event_id`, `service_name`, `service_environment`, `trace_id` | auto-populated |

All `event_action` values are defined in `EventAction` (an enum in `apps/audit/enums.py`). Examples: `user:session:login`, `applet:answer:export`, `user:mfa:enable`.

---

## How an event flows through the system

```
API process                                 Worker process
──────────────────────────────              ─────────────────────────────────────
1. await audit.log(event)
      │
      │  serialize to plain dict
      │  (model_dump, mode="json")
      │
      ▼
2. send_audit_event.kiq(payload)
      │
      │  pushes message onto RabbitMQ
      │  API returns here ← non-blocking
      │
      └──────── RabbitMQ queue ──────────►  3. send_audit_event(payload)
                                                  │
                                                  │  OpenSearchClient().index_document()
                                                  │
                                                  ▼
                                            POST /audit-logs/_doc
                                            → document stored in OpenSearch
```

**The API never waits for OpenSearch.** As soon as the message is on the queue (step 2), the HTTP response can return. The write to OpenSearch happens in a separate worker process.

---

## Where each piece lives

| File | What it does |
|---|---|
| `apps/audit/domain.py` | `AuditEvent` — the Pydantic model that defines every field an audit event can have |
| `apps/audit/enums.py` | `EventAction`, `EventOutcome` — the vocabulary of valid actions and outcomes |
| `apps/audit/service.py` | `audit.log()` — the one function callers use. Serializes and enqueues. |
| `apps/audit/tasks.py` | `send_audit_event` — the Taskiq worker task. Writes to OpenSearch, handles retries. |
| `apps/audit/index_mapping.py` | OpenSearch field type definitions for the `audit-logs` index |
| `infrastructure/utility/opensearch_client.py` | Singleton `AsyncOpenSearch` wrapper used by the worker |
| `infrastructure/lifespan.py` | Creates the `audit-logs` index on app startup (once, idempotent) |
| `config/opensearch.py` | `OpenSearchSettings` — host, port, credentials, index name |

---

## How to emit an audit event

```python
import audit
from apps.audit import AuditEvent, EventAction

await audit.log(
    AuditEvent(
        user_id=current_user.id,
        event_action=EventAction.USER_SESSION_LOGIN,
        client_ip=request.client.host,
        http_request_method=request.method,
        url_path=request.url.path,
        http_response_status_code=200,
    )
)
```

Only `user_id` and `event_action` are required. Everything else is optional and contextual.

---

## Failure handling

If OpenSearch is unavailable or returns an error:

1. The worker logs a warning and re-enqueues the task with a **5-second delay**.
2. This repeats up to **3 times** (configurable via `retries`).
3. After all retries are exhausted, the full event payload is logged at **ERROR level**, which captures it in Datadog. The event is not silently dropped.

---

## OpenSearch index

The `audit-logs` index is created once on app startup by `startup_opensearch()` in `lifespan.py`. The mapping is defined explicitly in `index_mapping.py` — field types are chosen for the queries we expect:

- `keyword` — IDs, enums, statuses (exact match, aggregation)
- `ip` — `client.ip` (CIDR range queries)
- `date` — `@timestamp` (time-range queries)
- `text` — URL paths, user agent strings (full-text search)

Adding new **event actions** (new values of `EventAction`) requires no mapping changes. Adding new **fields** to `AuditEvent` requires a corresponding entry in `index_mapping.py`.

---

## Configuration

All OpenSearch settings are nested under `OPENSEARCH__` in the environment:

```bash
OPENSEARCH__HOST=opensearch        # default: opensearch (Docker service name)
OPENSEARCH__PORT=9200              # default: 9200
OPENSEARCH__USER=admin             # default: admin
OPENSEARCH__PASSWORD=admin         # default: admin
OPENSEARCH__USE_SSL=True           # default: True (required by the Docker image)
OPENSEARCH__VERIFY_CERTS=False     # default: False (self-signed cert in local/dev)
OPENSEARCH__AUDIT_INDEX=audit-logs # default: audit-logs
```

For local development, if running the backend outside Docker, set `OPENSEARCH__HOST=localhost`.
