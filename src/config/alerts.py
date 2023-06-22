from pydantic import BaseModel


class AlertsSettings(BaseModel):
    ws_fetching_periodicity_sec: int = 5
