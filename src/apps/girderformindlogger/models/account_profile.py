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
from apps.girderformindlogger.utility.progress import (
    noProgress,
    setResponseTimeLimit,
)


class AccountProfile(AccessControlledModel):
    """
    collection for managing account profiles
    """

    def initialize(self):
        self.name = "accountProfile"
        self.ensureIndices(("userId", "accountId", "accountName"))

    def validate(self, document):
        if not document.get("accountName", ""):
            raise ValidationException(
                "accountName not defined.", "accountName"
            )

        return document

    def validateDBURL(self, db_uri: str):
        match = re.fullmatch(r"^mongodb://\w+:\w+@\w+:\d+/\w+", db_uri)
        # if not match:
        #     raise ValidationException('MongoDB url is not correct.')
        return True

    def createOwner(self, user):
        account = {
            "userId": user["_id"],
            "accountName": user["firstName"],
            "applets": {},
        }
        account = self.save(account)
        account["accountId"] = account["_id"]

        return self.save(account)

    def updateAccountName(self, accountId, accountName):
        self.update(
            {"accountId": ObjectId(accountId)},
            {"$set": {"accountName": accountName}},
        )

    def hasPermission(self, profile, role):
        if profile and (
            profile["_id"] == profile["accountId"]
            or len(profile.get("applets", {}).get(role, []))
        ):
            return True

        return False

    def getOwner(self, accountId):
        return self.findOne({"_id": ObjectId(accountId)})

    def getAccounts(self, userId):
        accounts = list(self.find({"userId": userId}))
        return accounts

    def createAccountProfile(self, accountId, userId):
        existingProfile = self.findOne(
            {"accountId": ObjectId(accountId), "userId": userId}
        )

        if existingProfile:
            return existingProfile

        ownerAccount = self.load(accountId, force=True)
        accountProfile = {
            "userId": userId,
            "accountName": ownerAccount["accountName"],
            "accountId": accountId,
            "applets": {},
        }
        return self.save(accountProfile)

    def appendApplet(self, profile, appletId, roles):
        appletId = ObjectId(appletId)

        if profile["accountId"] == profile["_id"]:
            roles = list(USER_ROLES.keys())
            roles.append("owner")

        for role in roles:
            profile["applets"][role] = profile["applets"].get(role, [])
            if appletId not in profile["applets"][role]:
                profile["applets"][role].append(appletId)

        return self.save(profile)

    def removeApplet(self, profile, appletId, rolesToRevoke=None):
        roles = list(USER_ROLES.keys()) if not rolesToRevoke else rolesToRevoke
        roles.append("owner")

        if not profile.get("applets", None):
            profile["applets"] = {}

        appletId = ObjectId(appletId)

        for role in roles:
            if appletId in profile["applets"].get(role, []):
                profile["applets"][role].remove(appletId)

        if profile["_id"] != profile["accountId"] and not len(
            profile.get("applets", {}).get("user", [])
        ):
            self.remove(profile)
        else:
            self.save(profile)
