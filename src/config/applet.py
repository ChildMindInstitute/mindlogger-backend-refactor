from pydantic import BaseModel


class AppletEMASettings(BaseModel):
    id: str | None = None
    name: str | None = None
    export_path_prefix: str = "export-ema"
    export_flow_file_name: str = "flow-items.csv"
    export_user_flow_schedule_file_name: str = "{date}-flow-schedule.csv"
    export_user_activity_schedule_file_name: str = "{date}-activity-schedule.csv"
