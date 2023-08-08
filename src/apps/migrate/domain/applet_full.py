import datetime

from apps.applets.domain.applet_full import AppletFull


class AppletMigratedFull(AppletFull):
    migrated_date: datetime.datetime
    migrated_updated: datetime.datetime


class AppletMigratedHistoryFull(AppletFull):
    migrated_date: datetime.datetime
    migrated_updated: datetime.datetime
