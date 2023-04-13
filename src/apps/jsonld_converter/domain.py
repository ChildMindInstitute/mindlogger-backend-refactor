import uuid

from apps.activities.domain.activity_create import (
    ActivityCreate,
    ActivityItemCreate,
)
from apps.applets.domain.applet_create import AppletCreate


class LdAppletCreate(AppletCreate):
    extra_fields: dict


class LdActivityCreate(ActivityCreate):
    extra_fields: dict


class LdActivityItemCreate(ActivityItemCreate):  # TODO
    extra_fields: dict
