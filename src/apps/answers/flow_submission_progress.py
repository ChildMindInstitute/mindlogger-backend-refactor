from __future__ import annotations

from collections import Counter
from typing import Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from apps.activity_flows.crud import FlowsHistoryCRUD
from apps.answers.crud.answers import AnswersCRUD


class FlowSubmissionProgress:
    """Track flow submission progress using occurrence counting."""

    def __init__(self, session: AsyncSession, answer_session: AsyncSession):
        self._session = session
        self._answer_session = answer_session
        self._expected_counts: Counter[str] = Counter()
        self._expected_ids: set[str] = set()
        self._submitted_counts: Counter[str] = Counter()
        self._has_flow_history: bool = False

    async def load(self, flow_history_id: str, submit_id) -> None:
        """Load flow structure and existing submissions for the submit id."""
        flow_histories = await FlowsHistoryCRUD(self._session).load_full([flow_history_id], load_activities=False)
        if not flow_histories:
            self._has_flow_history = False
            return

        flow_history = flow_histories[0]
        self._expected_counts = Counter(item.activity_id for item in flow_history.items)
        self._expected_ids = set(self._expected_counts.keys())
        self._has_flow_history = True

        existing_answers = await AnswersCRUD(self._answer_session).get_by_submit_id(submit_id)
        self._submitted_counts = Counter(answer.activity_history_id for answer in existing_answers or [])

    @property
    def has_flow_history(self) -> bool:
        return self._has_flow_history

    def is_complete_before_current(self) -> bool:
        return self._all_expected_satisfied(self._submitted_counts.items())

    def can_accept(self, activity_history_id: str) -> bool:
        expected_total = self._expected_counts.get(activity_history_id, 0)
        if expected_total == 0:
            return False
        return self._submitted_counts.get(activity_history_id, 0) < expected_total

    def completion_state_after_add(self, activity_history_id: str) -> bool:
        temp_counts = self._submitted_counts.copy()
        temp_counts[activity_history_id] += 1
        return self._all_expected_satisfied(temp_counts.items())

    def contains_activity(self, activity_history_id: str) -> bool:
        if not self._has_flow_history:
            return False
        return activity_history_id in self._expected_ids

    @property
    def expected_total(self) -> int:
        return sum(self._expected_counts.values())

    @property
    def submitted_total(self) -> int:
        return sum(self._submitted_counts.values())

    def _all_expected_satisfied(self, submitted_items: Iterable[tuple[str, int]]) -> bool:
        submitted_map = dict(submitted_items)
        for activity_history_id, expected_count in self._expected_counts.items():
            if submitted_map.get(activity_history_id, 0) < expected_count:
                return False
        return True
