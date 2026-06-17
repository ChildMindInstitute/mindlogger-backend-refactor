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
                                                  │  AuditLogCRUD(session).save(...)
                                                  │  INSERT ... ON CONFLICT DO NOTHING
                                                  ▼
                                            row stored in the `audit_logs`
                                            table (primary Postgres database)
```

**The API never waits for the audit write.** As soon as the message is on the queue (step 2), the HTTP response can return. The write to Postgres happens in a separate worker process.

Audit events are stored in the primary Postgres database. A few fields are denormalized into typed columns for filtering/sorting; the full ECS document is kept in a JSONB `payload` column and is what the export endpoint returns.

---

## Where each piece lives

| File | What it does |
|---|---|
| `apps/audit/domain.py` | `AuditEvent` — the Pydantic model that defines every field an audit event can have |
| `apps/audit/enums.py` | `EventAction`, `EventOutcome` — the vocabulary of valid actions and outcomes |
| `apps/audit/service.py` | `audit.log()` — the one function callers use. Serializes and enqueues. |
| `apps/audit/tasks.py` | `send_audit_event` — the Taskiq worker task. Writes to Postgres, handles retries. |
| `apps/audit/db/schemas.py` | `AuditLogSchema` — the `audit_logs` table (typed columns + JSONB `payload`) |
| `apps/audit/crud.py` | `AuditLogCRUD` — idempotent insert and the applet-scoped export query |
| `apps/audit/query_service.py` | `AuditQueryService` — rebuilds `AuditEvent`s from stored rows for the export endpoint |

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

If the database write fails:

1. The worker logs a warning and re-enqueues the task with a **5-second delay**.
2. This repeats up to **3 times** (configurable via `retries`).
3. After all retries are exhausted, the full event payload is logged at **ERROR level**, which captures it in Datadog. The event is not silently dropped.

Each event carries a unique `event_id`, stored in a unique column. The insert uses `ON CONFLICT (event_id) DO NOTHING`, so a retried task that re-delivers the same event never creates a duplicate row.

---

## Storage

Audit events live in the `audit_logs` table (`apps/audit/db/schemas.py`), created by an Alembic migration like any other table.

- Typed columns — `event_id`, `event_timestamp`, `event_action`, `event_outcome`, `user_id`, `applet_ids` — back the export query's filter and sort.
- `payload` (JSONB) holds the full event document; the export endpoint returns it verbatim.

Indexes:
- unique on `event_id` (idempotency)
- `(event_timestamp, event_id)` — the date-range filter and sort order
- GIN on `applet_ids` — `:applet_id = ANY(applet_ids)` membership lookups

Adding new **event actions** (new values of `EventAction`) requires no schema change. Adding new **fields** to `AuditEvent` requires no schema change either — they are stored in the JSONB `payload` automatically; only promote a field to its own column (with a migration) if you need to filter or sort on it.

> Note: the legacy OpenSearch modules (`infrastructure/utility/opensearch_client.py`, `apps/audit/index_mapping.py`, `config/opensearch.py`) remain in the tree but are no longer wired into the audit pipeline.

---

## Retention

There is currently no retention policy — the `audit_logs` table grows unbounded (the previous OpenSearch setup had no retention either). When retention becomes necessary, the recommended approach is native Postgres range partitioning by `event_timestamp` (e.g. monthly) with a scheduled job that drops partitions older than a configurable window.
