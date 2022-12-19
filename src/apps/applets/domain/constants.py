from apps.shared.domain import Enum


class Role(str, Enum):
    ADMIN = "admin"
    CONTENT_MANAGER = "content manager"
    DATA_MANAGER = "data manager"
    CASE_MANAGER = "case manager"
    RESPONDENTS_MANAGER = "respondents manager"
    REVIEWERS_MANAGER = "reviewers manager"
    MANAGERS_MANAGER = "managers manager"
    REVIEWER = "reviewer"
    RESPONDENT = "respondent"
