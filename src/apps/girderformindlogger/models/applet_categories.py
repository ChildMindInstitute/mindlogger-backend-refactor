# -*- coding: utf-8 -*-
import copy
import datetime
import json
import os
import re

import six
from bson import json_util
from bson.objectid import ObjectId

from apps.girderformindlogger import events
from apps.girderformindlogger.constants import USER_ROLES, AccessType
from apps.girderformindlogger.exceptions import (
    GirderException,
    ValidationException,
)
from apps.girderformindlogger.models.model_base import (
    AccessControlledModel,
    Model,
)
from apps.girderformindlogger.utility.model_importer import ModelImporter


class AppletCategory(AccessControlledModel):
    """
    collection for managing account profiles
    """

    def initialize(self):
        self.name = "appletCategories"
        self.ensureIndices(
            (
                "name",
                "parentId",
            )
        )

    def validate(self, document):
        if not document.get("name", ""):
            raise ValidationException("name not defined.", "name")

        return document

    def addCategory(self, name, parentId=None):
        category = {
            "name": name,
            "parentId": None if not parentId else ObjectId(parentId),
            "type": "sub-category" if parentId else "category",
        }

        return self.save(category)

    def getCategoryByName(self, name):
        return self.findOne({"name": name})
