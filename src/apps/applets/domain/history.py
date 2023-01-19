from apps.shared.domain import InternalModel, PublicModel

__all__ = ['AppletHistory', 'AppletHistoryChange', 'PublicAppletHistoryChange']


class AppletHistory(InternalModel):
    display_name: str
    description: dict
    about: dict
    image: str
    watermark: str
    theme_id: int | None
    version: str
    account_id: int
    creator_id: int
    report_server_ip: str
    report_public_key: str
    report_recipients: str
    report_include_user_id: str
    report_include_case_id: str
    report_email_body: str


class AppletHistoryChange(AppletHistory):
    display_name: str
    description: dict
    about: dict
    image: str
    watermark: str
    theme_id: str
    version: str
    account_id: str
    creator_id: str
    report_server_ip: str
    report_public_key: str
    report_recipients: str
    report_include_user_id: str
    report_include_case_id: str
    report_email_body: str


class PublicAppletHistoryChange(PublicModel, AppletHistoryChange):
    pass
