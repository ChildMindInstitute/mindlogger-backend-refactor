from gettext import gettext as _

from apps.shared.exception import AccessDeniedError, FieldError, InternalServerError, NotFoundError, ValidationError


class EventNotFoundError(NotFoundError):
    message_is_template: bool = True
    message = _("No such event with {key}={value}.")


class PeriodicityNotFoundError(NotFoundError):
    message_is_template: bool = True
    message = _("No such periodicity with {key}={value}.")


class AppletScheduleNotFoundError(NotFoundError):
    message_is_template: bool = True
    message = _("No schedules found for applet {applet_id}")


class AccessDeniedToApplet(AccessDeniedError):
    message = _("Access denied to applet.")


class ActivityOrFlowNotFoundError(NotFoundError):
    message = _("Activity/Flow not found.")


class ScheduleNotFoundError(NotFoundError):
    message = _("Schedule not found.")


class EventAlwaysAvailableExistsError(ValidationError):
    message = _("'AlwaysAvailable' event already exists.")


class EventError(InternalServerError):
    message = _("Event service error.")


class UserEventAlreadyExists(ValidationError):
    message_is_template: bool = True
    message = _("The event {event_id} for user {user_id} already exists.")


class ActivityEventAlreadyExists(ValidationError):
    message_is_template: bool = True
    message = _("The event {event_id} for activity {activity_id} already exists.")


class FlowEventAlreadyExists(ValidationError):
    message_is_template: bool = True
    message = _("The event {event_id} for flow {flow_id} already exists.")


class SelectedDateRequiredError(FieldError):
    message = _("selectedDate is required for this periodicity type.")


class HourRangeError(FieldError):
    message = _("Hours must be between 0 and 23.")


class MinuteRangeError(FieldError):
    message = _("Minutes must be between 0 and 59.")


class ActivityOrFlowRequiredError(FieldError):
    message = _("Either activity_id or flow_id must be provided.")


class OneTimeCompletionCaseError(FieldError):
    message = _("one_time_completion must be set if periodicity is ALWAYS.")


class StartEndTimeAccessBeforeScheduleCaseError(FieldError):
    message = _("start_time, end_time, access_before_schedule must be set if periodicity is not ALWAYS.")


class StartEndTimeEqualError(FieldError):
    message = _("The start_time and end_time fields can't be equal.")


class UnavailableActivityOrFlowError(FieldError):
    message = _("Activity/flow is unavailable at this time.")


class AtTimeFieldRequiredError(FieldError):
    zero_path = None
    message = _("at_time is required for this trigger type.")


class TimerRequiredError(FieldError):
    zero_path = None
    message = _("Timer is required for this timer type.")


class FromTimeToTimeRequiredError(FieldError):
    zero_path = None
    message = _("from_time and to_time are required for this trigger type.")
