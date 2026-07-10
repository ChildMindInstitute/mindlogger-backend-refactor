from .enums import EventAction, EventCategory, EventType

# Account-level events (logged without ``curious.applet_id``) surfaced in an applet's audit export,
# but only for users with a manager-class role on that applet. Kept as an explicit whitelist:
# some applet-scoped failures also lack an applet id.
ACCOUNT_LEVEL_EXPORT_ACTIONS: frozenset[EventAction] = frozenset(
    {
        EventAction.USER_SESSION_LOGIN,
        EventAction.USER_SESSION_LOGOUT,
        EventAction.USER_SESSION_REFRESH,
        EventAction.USER_SESSION_INVALID,
        EventAction.USER_CREATE,
        EventAction.USER_DELETE,
        EventAction.USER_PASSWORD_CHANGE,
        EventAction.USER_PASSWORD_RECOVERY_INITIATE,
        EventAction.USER_PASSWORD_RECOVERY_APPROVE,
        EventAction.USER_MFA_ENABLE,
        EventAction.USER_MFA_DISABLE,
        EventAction.USER_MFA_RECOVERY_VIEW,
        EventAction.USER_MFA_RECOVERY_DOWNLOAD,
        EventAction.USER_MFA_RECOVERY_USE,
    }
)

EVENT_ACTION_TO_EVENT_CATEGORY: dict[EventAction, tuple[EventCategory, ...]] = {
    # User auth
    EventAction.USER_SESSION_LOGIN: (EventCategory.SESSION, EventCategory.AUTHENTICATION),
    EventAction.USER_SESSION_LOGOUT: (EventCategory.SESSION,),
    EventAction.USER_SESSION_REFRESH: (EventCategory.SESSION, EventCategory.AUTHENTICATION),
    EventAction.USER_SESSION_INVALID: (EventCategory.SESSION, EventCategory.AUTHENTICATION),
    # User IAM
    EventAction.USER_CREATE: (EventCategory.IAM,),
    EventAction.USER_DELETE: (EventCategory.IAM,),
    EventAction.USER_PASSWORD_CHANGE: (EventCategory.IAM,),
    EventAction.USER_PASSWORD_RECOVERY_INITIATE: (EventCategory.IAM,),
    EventAction.USER_PASSWORD_RECOVERY_APPROVE: (EventCategory.IAM,),
    EventAction.USER_MFA_ENABLE: (EventCategory.IAM,),
    EventAction.USER_MFA_DISABLE: (EventCategory.IAM,),
    EventAction.USER_MFA_RECOVERY_VIEW: (EventCategory.IAM,),
    EventAction.USER_MFA_RECOVERY_DOWNLOAD: (EventCategory.IAM,),
    EventAction.USER_MFA_RECOVERY_USE: (EventCategory.IAM,),
    # Applet IAM
    EventAction.APPLET_CREATE: (EventCategory.IAM, EventCategory.CONFIGURATION),
    EventAction.APPLET_DELETE: (EventCategory.IAM, EventCategory.CONFIGURATION),
    EventAction.APPLET_ENCRYPTION_UPDATE: (EventCategory.IAM, EventCategory.CONFIGURATION),
    EventAction.APPLET_TRANSFER_INITIATE: (EventCategory.IAM,),
    EventAction.APPLET_TRANSFER_ACCEPT: (EventCategory.IAM,),
    EventAction.APPLET_TRANSFER_DECLINE: (EventCategory.IAM,),
    EventAction.APPLET_INVITE_INITIATE: (EventCategory.IAM,),
    EventAction.APPLET_INVITE_ACCEPT: (EventCategory.IAM,),
    EventAction.APPLET_INVITE_DECLINE: (EventCategory.IAM,),
    EventAction.APPLET_ACCESS_GRANT: (EventCategory.IAM,),
    EventAction.APPLET_ACCESS_REVOKE: (EventCategory.IAM,),
    EventAction.APPLET_RETENTION_UPDATE: (EventCategory.IAM, EventCategory.CONFIGURATION),
    EventAction.APPLET_REPORT_UPDATE: (EventCategory.IAM, EventCategory.CONFIGURATION),
    # Applet data access
    EventAction.APPLET_SUBJECT_VIEW: (EventCategory.DATABASE,),
    EventAction.APPLET_ANSWER_VIEW: (EventCategory.DATABASE,),
    EventAction.APPLET_ANSWER_IDENTIFIER_VIEW: (EventCategory.DATABASE,),
    EventAction.APPLET_ANSWER_ASSESSMENT_VIEW: (EventCategory.DATABASE,),
    EventAction.APPLET_ANSWER_NOTE_VIEW: (EventCategory.DATABASE,),
    EventAction.APPLET_ANSWER_EXPORT: (EventCategory.DATABASE,),
    # Applet audit
    EventAction.APPLET_AUDIT_EXPORT: (EventCategory.DATABASE,),
    # Applet file download
    EventAction.APPLET_ANSWER_EHR_DOWNLOAD: (EventCategory.FILE,),
    EventAction.APPLET_ANSWER_FILE_DOWNLOAD: (EventCategory.FILE,),
    EventAction.APPLET_ANSWER_REPORT_DOWNLOAD: (EventCategory.FILE,),
}

EVENT_ACTION_TO_EVENT_TYPE: dict[EventAction, tuple[EventType, ...]] = {
    # User auth
    EventAction.USER_SESSION_LOGIN: (EventType.START,),
    EventAction.USER_SESSION_LOGOUT: (EventType.END,),
    EventAction.USER_SESSION_REFRESH: (EventType.INFO,),
    EventAction.USER_SESSION_INVALID: (EventType.INFO,),
    # User IAM
    EventAction.USER_CREATE: (EventType.CREATION,),
    EventAction.USER_DELETE: (EventType.DELETION,),
    EventAction.USER_PASSWORD_CHANGE: (EventType.CHANGE,),
    EventAction.USER_PASSWORD_RECOVERY_INITIATE: (EventType.INFO,),
    EventAction.USER_PASSWORD_RECOVERY_APPROVE: (EventType.CHANGE,),
    EventAction.USER_MFA_ENABLE: (EventType.CHANGE,),
    EventAction.USER_MFA_DISABLE: (EventType.CHANGE,),
    EventAction.USER_MFA_RECOVERY_VIEW: (EventType.ACCESS,),
    EventAction.USER_MFA_RECOVERY_DOWNLOAD: (EventType.ACCESS,),
    EventAction.USER_MFA_RECOVERY_USE: (EventType.CHANGE,),
    # Applet IAM
    EventAction.APPLET_CREATE: (EventType.CREATION,),
    EventAction.APPLET_DELETE: (EventType.DELETION,),
    EventAction.APPLET_ENCRYPTION_UPDATE: (EventType.CHANGE,),
    EventAction.APPLET_TRANSFER_INITIATE: (EventType.INFO,),
    EventAction.APPLET_TRANSFER_ACCEPT: (EventType.CHANGE,),
    EventAction.APPLET_TRANSFER_DECLINE: (EventType.INFO,),
    EventAction.APPLET_INVITE_INITIATE: (EventType.INFO,),
    EventAction.APPLET_INVITE_ACCEPT: (EventType.CHANGE,),
    EventAction.APPLET_INVITE_DECLINE: (EventType.INFO,),
    EventAction.APPLET_ACCESS_GRANT: (EventType.CHANGE,),
    EventAction.APPLET_ACCESS_REVOKE: (EventType.CHANGE,),
    EventAction.APPLET_RETENTION_UPDATE: (EventType.CHANGE,),
    EventAction.APPLET_REPORT_UPDATE: (EventType.CHANGE,),
    # Applet data access
    EventAction.APPLET_SUBJECT_VIEW: (EventType.ACCESS,),
    EventAction.APPLET_ANSWER_VIEW: (EventType.ACCESS,),
    EventAction.APPLET_ANSWER_IDENTIFIER_VIEW: (EventType.ACCESS,),
    EventAction.APPLET_ANSWER_ASSESSMENT_VIEW: (EventType.ACCESS,),
    EventAction.APPLET_ANSWER_NOTE_VIEW: (EventType.ACCESS,),
    EventAction.APPLET_ANSWER_EXPORT: (EventType.ACCESS,),
    # Applet audit
    EventAction.APPLET_AUDIT_EXPORT: (EventType.ACCESS,),
    # Applet file download
    EventAction.APPLET_ANSWER_EHR_DOWNLOAD: (EventType.ACCESS,),
    EventAction.APPLET_ANSWER_FILE_DOWNLOAD: (EventType.ACCESS,),
    EventAction.APPLET_ANSWER_REPORT_DOWNLOAD: (EventType.ACCESS,),
}
