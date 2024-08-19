from gettext import gettext as _

from apps.shared.exception import ValidationError


class UniqueIntegrationError(ValidationError):
    message = _("Integrations must be unique.")


class IntegrationsConfigurationsTypeAlreadyAssignedToAppletError(ValidationError):
    message = _("Provided Integration Type `{type}` has previously been tied to applet `{applet_id}`.")


class UnexpectedPropertiesForIntegration(ValidationError):
    message = _("Provided configurations `{provided_keys}` for Integration Type `{type}` were not expected. Expected keys are: `{expected_keys}`")


class UnsupportedIntegrationError(ValidationError):
    message = _("The specified integration type `{type}` is not supported")


class UnavailableIntegrationError(ValidationError):
    message = _("The specified integration type `{type}` does not exist for applet `{applet_id}`")
