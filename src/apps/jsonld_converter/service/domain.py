from dataclasses import dataclass, field


@dataclass
class ActivityItemExportData:
    id: str
    schema: dict


@dataclass
class ActivityExportData:
    id: str
    schema: dict
    activity_items: list[ActivityItemExportData] = field(default_factory=list)


class ActivityFlowExportData:
    id: str
    schema: dict


@dataclass
class ProtocolExportData:
    id: str
    schema: dict
    activities: list[ActivityExportData] = field(default_factory=list)
    activity_flows: list[ActivityFlowExportData] = field(default_factory=list)


ModelExportData = (
    ProtocolExportData | ActivityExportData | ActivityItemExportData
)
