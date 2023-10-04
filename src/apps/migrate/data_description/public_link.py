import uuid
from dataclasses import dataclass

from bson import ObjectId
from apps.migrate.utilities import mongoid_to_uuid


@dataclass
class PublicLinkDao:
    link: str
    require_login: bool
    applet_bson: ObjectId
    created_by_bson: ObjectId

    @property
    def link_id(self) -> uuid.UUID:
        if len(self.link) == 18:
            link_str = f"{self.link}-{'0'*4}-{'0'*12}"
            return uuid.UUID(link_str)
        else:
            return uuid.UUID(self.link)

    @property
    def applet_id(self) -> uuid.UUID:
        return mongoid_to_uuid(self.applet_bson)

    @property
    def created_by(self) -> uuid.UUID:
        return mongoid_to_uuid(self.created_by_bson)
