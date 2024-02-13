# -*- coding: utf-8 -*-
import datetime
import json
import os

from bson.objectid import ObjectId

from apps.girderformindlogger.constants import DEFINED_RELATIONS, PROFILE_FIELDS, AccessType, SortDir
from apps.girderformindlogger.exceptions import AccessException, ValidationException
from apps.girderformindlogger.models.aes_encrypt import AccessControlledModel, AESEncryption
from apps.girderformindlogger.models.profile import Profile
from apps.girderformindlogger.utility.progress import noProgress


class Note(AESEncryption, dict):
    def initialize(self):
        self.name = "notes"
        self.ensureIndices(
            (
                "appletId",
                "reviewerId",
                "note",
                "updated",
                "created",
                "userProfileId",
                "responseId",
            )
        )

        self.initAES(
            [
                ("note", 256),
            ]
        )

    def validate(self, document):
        if not document.get("appletId", "") or not document.get(
            "reviewerId", ""
        ):
            raise ValidationException("document is invalid.")

        return document

    def addNote(self, appletId, responseId, userProfileId, note, reviewer):
        document = {
            "appletId": ObjectId(appletId),
            "responseId": ObjectId(responseId),
            "userProfileId": ObjectId(userProfileId),
            "note": note,
            "reviewerId": reviewer["_id"],
            "created": datetime.datetime.utcnow(),
            "updated": datetime.datetime.utcnow(),
        }

        document = self.save(document)
        document["reviewer"] = {
            "firstName": reviewer.get("firstName", ""),
            "lastName": reviewer.get("lastName", ""),
        }
        document["my_note"] = True

        return document

    def updateNote(self, noteId, note, reviewer):
        document = self.findOne({"_id": ObjectId(noteId)})

        if document:
            if document["reviewerId"] != reviewer["_id"]:
                raise AccessException("permission denied")

            document.update(
                {"note": note, "updated": datetime.datetime.utcnow()}
            )

            document = self.save(document)

            document["reviewer"] = {
                "firstName": reviewer.get("firstName", ""),
                "lastName": reviewer.get("lastName", ""),
            }
            document["my_note"] = True

            return document

        return None

    def deleteNote(self, noteId):
        self.removeWithQuery({"_id": ObjectId(noteId)})

    def getNotes(self, responseId, reviewer):
        notes = list(
            self.find(
                {"responseId": ObjectId(responseId)},
                sort=[("created", SortDir.DESCENDING)],
            )
        )

        profiles = Profile().find(
            {"_id": {"$in": [note["reviewerId"] for note in notes]}}
        )

        # reviewer names
        names = {}
        for profile in profiles:
            names[str(profile["_id"])] = {
                "firstName": profile.get("firstName", ""),
                "lastName": profile.get("lastName", ""),
            }

        for note in notes:
            note["reviewer"] = names[str(note["reviewerId"])]
            note["my_note"] = reviewer["_id"] == note["reviewerId"]

        return notes
