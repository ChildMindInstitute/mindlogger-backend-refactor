import uuid
from typing import List

from apps.invitations.domain import InvitationManagersRequest, InvitationRespondentRequest, InvitationReviewerRequest
from apps.workspaces.domain.constants import ManagersRole


def build_manager_invitation(email: str, role: ManagersRole, **kwargs) -> InvitationManagersRequest:
    attrs = {
        "first_name": "Tester",
        "last_name": "Testerson",
        "language": "en",
    }
    attrs.update(kwargs)

    return InvitationManagersRequest(**attrs, email=email, role=role)


def build_respondent_invitation(email: str, secret_user_id: str, **kwargs) -> InvitationRespondentRequest:
    attrs = {
        "first_name": "Tester",
        "last_name": "Testerson",
        "language": "en",
    }
    attrs.update(kwargs)

    return InvitationRespondentRequest(**attrs, email=email, secret_user_id=secret_user_id)


def build_reviewer_invitation(email: str, subject_ids: List[uuid.UUID], **kwargs) -> InvitationReviewerRequest:
    attrs = {
        "first_name": "Tester",
        "last_name": "Testerson",
        "language": "en",
    }
    attrs.update(kwargs)

    return InvitationReviewerRequest(**attrs, email=email, subjects=subject_ids)
