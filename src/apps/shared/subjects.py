from datetime import datetime

from apps.subjects.domain import SubjectRelation


def is_take_now_relation(relation: SubjectRelation | None) -> bool:
    return relation is not None and relation.relation == "take-now" and relation.meta is not None


def is_valid_take_now_relation(relation: SubjectRelation | None) -> bool:
    if is_take_now_relation(relation):
        assert isinstance(relation, SubjectRelation)
        assert isinstance(relation.meta, dict)
        if "expiresAt" in relation.meta:
            expires_at = datetime.fromisoformat(relation.meta["expiresAt"])
            return expires_at > datetime.now()

    return False
