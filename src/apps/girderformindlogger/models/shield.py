# -*- coding: utf-8 -*-
import datetime

import pymongo

from apps.girderformindlogger.models.model_base import Model
from apps.girderformindlogger.models.setting import Setting


class Shield(Model):
    def initialize(self):
        self.name = "shield"

    def set_default(self, user, ctx):
        self.save(
            {
                "user": user.get("_id"),
                "source": ctx,
                "date": datetime.datetime.now(),
                "blocked": False,
                "count": 1,
                "date_blocked": None,
            },
            validate=False,
        )
