from gettext import gettext as _

from apps.shared.exception import ValidationError


class UniqueIntegrationError(ValidationError):
    message = _("Integrations must be unique.")


class IntegrationsConfigurationsTypeAlreadyAssignedToAppletError(ValidationError):
    message = _("Provided Integration Type `{type}` has previously been tied to applet `{applet_id}`.")


class UnsupportedIntegrationError(ValidationError):
    message = _("The specified integration type `{type}` is not supported")
