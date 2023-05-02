from gettext import gettext as _

from apps.shared.exception import AccessDeniedError, NotFoundError, \
    ValidationError, InternalServerError


class EventNotFoundError(NotFoundError):
    message = _("No such event with {key}={value}.")


class PeriodicityNotFoundError(NotFoundError):
    message = _("No such periodicity with {key}={value}.")


class AppletScheduleNotFoundError(NotFoundError):
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
    message = _("Event service error")


class UserEventAlreadyExists(ValidationError):
    message = _("The event {event_id} for user {user_id} already exists.")


class ActivityEventAlreadyExists(ValidationError):
    message = _(
        "The event {event_id} for activity {activity_id} already exists.")


class FlowEventAlreadyExists(ValidationError):
    message = _("The event {event_id} for flow {flow_id} already exists.")
