from pydantic import BaseModel


class AppletEMASettings(BaseModel):
    id: str | None = None
    name: str | None = None
    export_path_prefix: str = "export-ema"
    export_flow_file_name: str = "flow-items.csv"
