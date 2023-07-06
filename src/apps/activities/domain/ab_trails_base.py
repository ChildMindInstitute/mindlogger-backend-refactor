from apps.shared.domain import PublicModel


class Node(PublicModel):
    order_index: int
    cx: float
    cy: float
    label: str


class ABTrailsNodes(PublicModel):
    radius: float
    font_size: float
    font_size_begin_end: float | None = None
    begin_word_length: float | None = None
    end_word_length: float | None = None
    nodes: list[Node]


class Tutorial(PublicModel):
    text: str
    node_label: str | None = None


class ABTrailsTutorial(PublicModel):
    tutorials: list[Tutorial]
