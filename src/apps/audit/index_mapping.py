"""OpenSearch index mapping for audit log events.

Mirrors the ECS-aliased fields on AuditEvent (apps/audit/domain.py).
Field types are chosen for the access patterns we expect:
  - keyword: exact match / filter / aggregation (IDs, enums, statuses)
  - text:    full-text search (URLs, user agent strings)
  - date:    time-range queries
  - ip:      IP / CIDR range queries

Dotted aliases like "curious.applet_id" become nested objects in the mapping
because OpenSearch does not allow dots in mapping field names but does
interpret dots in document keys as nested paths.
"""

AUDIT_LOG_MAPPING: dict = {
    "mappings": {
        "properties": {
            "@timestamp": {"type": "date"},
            "error": {"properties": {"type": {"type": "keyword"}}},
            "event": {
                "properties": {
                    "action": {"type": "keyword"},
                    "id": {"type": "keyword"},
                    "kind": {"type": "keyword"},
                    "outcome": {"type": "keyword"},
                    "module": {"type": "keyword"},
                    "dataset": {"type": "keyword"},
                }
            },
            "service": {
                "properties": {
                    "name": {"type": "keyword"},
                    "environment": {"type": "keyword"},
                }
            },
            "user": {
                "properties": {
                    "id": {"type": "keyword"},
                    "roles": {"type": "keyword"},
                    "target": {
                        "properties": {
                            "id": {"type": "keyword"},
                            "email": {"type": "keyword"},
                            "roles": {"type": "keyword"},
                        }
                    },
                }
            },
            "client": {"properties": {"ip": {"type": "ip"}}},
            "http": {
                "properties": {
                    "request": {
                        "properties": {
                            "id": {"type": "keyword"},
                            "method": {"type": "keyword"},
                        }
                    },
                    "response": {"properties": {"status_code": {"type": "integer"}}},
                }
            },
            "trace": {"properties": {"id": {"type": "keyword"}}},
            "url": {
                "properties": {
                    "path": {"type": "text"},
                    "query": {"type": "text"},
                }
            },
            "user_agent": {"properties": {"original": {"type": "text"}}},
            "file": {"properties": {"path": {"type": "keyword"}}},
            "curious": {
                "properties": {
                    "applet_id": {"type": "keyword"},
                    "subject_id": {"type": "keyword"},
                    "flow_id": {"type": "keyword"},
                    "activity_id": {"type": "keyword"},
                    "submit_id": {"type": "keyword"},
                    "answer_id": {"type": "keyword"},
                }
            },
        }
    }
}