from pydantic import BaseModel


class DataMigrationSettings(BaseModel):
    filtering_applet_id: bool = False
    filtering_creator_id: bool = False
