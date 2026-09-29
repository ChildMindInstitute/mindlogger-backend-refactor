# Unit tests for AnswerService._filter_activity_flows.
# Pure in-memory — no DB or async fixtures needed.

import datetime
import itertools
import uuid

from apps.answers.domain.answers import AppletCompletedEntities, CompletedEntity
from apps.answers.service import AnswerService

APPLET_ID = uuid.uuid4()
FLOW_ID = uuid.uuid4()
EVENT_ID = "event-1"
SUBJECT_ID = uuid.uuid4()

T0 = datetime.datetime(2025, 1, 1, 0, 0, 0)


def _ts(minutes: int) -> datetime.datetime:
    return T0 + datetime.timedelta(minutes=minutes)


def _make_entity(
    *,
    flow_id: uuid.UUID = FLOW_ID,
    submit_id: uuid.UUID | None = None,
    version: str = "1.0.0",
    activity_flow_order: int = 1,
    is_flow_completed: bool = False,
    end_time: datetime.datetime | None = None,
    start_time: datetime.datetime | None = None,
    event_id: str | None = EVENT_ID,
    target_subject_id: uuid.UUID | None = SUBJECT_ID,
) -> CompletedEntity:
    _submit_id = submit_id or uuid.uuid4()
    _end_time = end_time or _ts(0)
    _start_time = start_time or _end_time - datetime.timedelta(minutes=1)
    flow_history_id = f"{flow_id}_{version}"
    return CompletedEntity(
        id=flow_history_id,  # validator expects "uuid_version" string, extracts uuid
        answer_id=uuid.uuid4(),
        submit_id=_submit_id,
        version=version,
        flow_history_id=flow_history_id,
        target_subject_id=target_subject_id,
        scheduled_event_id=event_id,
        local_end_date=_end_time.date(),
        local_end_time=_end_time.time(),
        start_time=_start_time,
        end_time=_end_time,
        is_flow_completed=is_flow_completed,
        activity_flow_order=activity_flow_order,
    )


def _make_result(flows: list[CompletedEntity]) -> AppletCompletedEntities:
    return AppletCompletedEntities(id=APPLET_ID, activities=[], activity_flows=flows)


# Groups by submit_id and keeps only the farthest-along entry per submission
class TestPerSubmitIdCollapsing:
    def test_keeps_highest_order_per_submit_id(self):
        sid = uuid.uuid4()
        e1 = _make_entity(submit_id=sid, activity_flow_order=1, end_time=_ts(1))
        e2 = _make_entity(submit_id=sid, activity_flow_order=2, end_time=_ts(2))
        e3 = _make_entity(submit_id=sid, activity_flow_order=3, end_time=_ts(3))

        result = _make_result([e1, e3, e2])
        AnswerService._filter_activity_flows(result)

        assert len(result.activity_flows) == 1
        assert result.activity_flows[0].activity_flow_order == 3

    def test_uses_end_time_as_tiebreaker_within_same_submit_id(self):
        sid = uuid.uuid4()
        e1 = _make_entity(submit_id=sid, activity_flow_order=2, end_time=_ts(1))
        e2 = _make_entity(submit_id=sid, activity_flow_order=2, end_time=_ts(5))

        result = _make_result([e1, e2])
        AnswerService._filter_activity_flows(result)

        assert len(result.activity_flows) == 1
        assert result.activity_flows[0].end_time == _ts(5)


# Most recently completed submission wins when multiple completions exist
class TestBestCompleted:
    def test_single_completed(self):
        e = _make_entity(is_flow_completed=True, end_time=_ts(10))
        result = _make_result([e])
        AnswerService._filter_activity_flows(result)

        assert len(result.activity_flows) == 1
        assert result.activity_flows[0].is_flow_completed is True

    def test_most_recent_completed_wins(self):
        sid1 = uuid.uuid4()
        sid2 = uuid.uuid4()
        e1 = _make_entity(submit_id=sid1, is_flow_completed=True, end_time=_ts(5))
        e2 = _make_entity(submit_id=sid2, is_flow_completed=True, end_time=_ts(10))

        result = _make_result([e1, e2])
        AnswerService._filter_activity_flows(result)

        assert len(result.activity_flows) == 1
        assert result.activity_flows[0].submit_id == sid2


# Farthest-along in-progress submission wins (after discarding stale ones)
class TestBestInProgress:
    def test_single_in_progress(self):
        e = _make_entity(activity_flow_order=2, end_time=_ts(5))
        result = _make_result([e])
        AnswerService._filter_activity_flows(result)

        assert len(result.activity_flows) == 1
        assert result.activity_flows[0].activity_flow_order == 2

    def test_farthest_along_wins_when_no_completion_exists(self):
        # without any completion, farthest-along wins regardless of recency
        sid1 = uuid.uuid4()
        sid2 = uuid.uuid4()
        e1 = _make_entity(submit_id=sid1, activity_flow_order=3, end_time=_ts(1))
        e2 = _make_entity(submit_id=sid2, activity_flow_order=1, end_time=_ts(5))

        result = _make_result([e1, e2])
        AnswerService._filter_activity_flows(result)

        assert len(result.activity_flows) == 1
        assert result.activity_flows[0].submit_id == sid1  # order=3 beats order=1


# When both a completed and an in-progress submission exist, pick the more recent one
class TestCompletedVsInProgress:
    def test_in_progress_newer_than_completed_wins(self):
        sid_c = uuid.uuid4()
        sid_ip = uuid.uuid4()
        completed = _make_entity(submit_id=sid_c, is_flow_completed=True, end_time=_ts(5))
        in_progress = _make_entity(submit_id=sid_ip, activity_flow_order=1, end_time=_ts(10))

        result = _make_result([completed, in_progress])
        AnswerService._filter_activity_flows(result)

        assert len(result.activity_flows) == 1
        assert result.activity_flows[0].submit_id == sid_ip

    def test_stale_in_progress_is_discarded_completed_wins(self):
        # in-progress older than the completion is stale and gets filtered out
        sid_c = uuid.uuid4()
        sid_ip = uuid.uuid4()
        completed = _make_entity(submit_id=sid_c, is_flow_completed=True, end_time=_ts(10))
        in_progress = _make_entity(submit_id=sid_ip, activity_flow_order=3, end_time=_ts(1))

        result = _make_result([completed, in_progress])
        AnswerService._filter_activity_flows(result)

        assert len(result.activity_flows) == 1
        assert result.activity_flows[0].submit_id == sid_c


# Reproduces the restart bug:
# Web1 starts (A, order=3), restarts and completes (B), then starts again (C, order=1).
# Before fix: stale A (order=3) beat C (order=1) as best_in_progress, then B (completed)
# beat A on recency, losing C entirely. Fix: A is discarded because end_time(A) < end_time(B).
class TestRestartBugScenario:
    def setup_method(self):
        self.sid_a = uuid.uuid4()  # original attempt — stale, order=3
        self.sid_b = uuid.uuid4()  # restarted and completed
        self.sid_c = uuid.uuid4()  # new attempt after completion, order=1

        self.entity_a = _make_entity(
            submit_id=self.sid_a, activity_flow_order=3, is_flow_completed=False, end_time=_ts(10)
        )
        self.entity_b = _make_entity(
            submit_id=self.sid_b, activity_flow_order=4, is_flow_completed=True, end_time=_ts(20)
        )
        self.entity_c = _make_entity(
            submit_id=self.sid_c, activity_flow_order=1, is_flow_completed=False, end_time=_ts(30)
        )

    def test_new_in_progress_is_returned(self):
        result = _make_result([self.entity_a, self.entity_b, self.entity_c])
        AnswerService._filter_activity_flows(result)

        assert len(result.activity_flows) == 1
        assert result.activity_flows[0].submit_id == self.sid_c

    def test_stale_in_progress_is_discarded(self):
        result = _make_result([self.entity_a, self.entity_b, self.entity_c])
        AnswerService._filter_activity_flows(result)

        assert self.sid_a not in {e.submit_id for e in result.activity_flows}

    def test_without_new_attempt_completed_is_returned(self):
        # if no new attempt yet, stale A is filtered out and completed B wins
        result = _make_result([self.entity_a, self.entity_b])
        AnswerService._filter_activity_flows(result)

        assert len(result.activity_flows) == 1
        assert result.activity_flows[0].submit_id == self.sid_b
        assert result.activity_flows[0].is_flow_completed is True

    def test_result_is_independent_of_input_order(self):
        entities = [self.entity_a, self.entity_b, self.entity_c]
        for perm in itertools.permutations(entities):
            result = _make_result(list(perm))
            AnswerService._filter_activity_flows(result)

            assert len(result.activity_flows) == 1
            assert result.activity_flows[0].submit_id == self.sid_c


class TestEdgeCases:
    def test_empty_activity_flows(self):
        result = _make_result([])
        AnswerService._filter_activity_flows(result)
        assert result.activity_flows == []

    def test_entities_for_different_flows_are_independent(self):
        flow_x = uuid.uuid4()
        flow_y = uuid.uuid4()
        ex = _make_entity(flow_id=flow_x, activity_flow_order=2, end_time=_ts(5))
        ey = _make_entity(flow_id=flow_y, activity_flow_order=1, end_time=_ts(10))

        result = _make_result([ex, ey])
        AnswerService._filter_activity_flows(result)

        assert len(result.activity_flows) == 2

    def test_in_progress_equal_to_completion_time_is_filtered_out(self):
        # strictly newer means > not >=, so equal time counts as stale
        sid_c = uuid.uuid4()
        sid_ip = uuid.uuid4()
        same_time = _ts(10)
        completed = _make_entity(submit_id=sid_c, is_flow_completed=True, end_time=same_time)
        in_progress = _make_entity(submit_id=sid_ip, activity_flow_order=1, end_time=same_time)

        result = _make_result([completed, in_progress])
        AnswerService._filter_activity_flows(result)

        assert len(result.activity_flows) == 1
        assert result.activity_flows[0].submit_id == sid_c

    def test_stale_filter_uses_most_recent_completion_not_oldest(self):
        # in-progress between old and new completion is stale relative to the new one
        sid_old = uuid.uuid4()
        sid_new = uuid.uuid4()
        sid_ip = uuid.uuid4()
        old_completed = _make_entity(submit_id=sid_old, is_flow_completed=True, end_time=_ts(5))
        new_completed = _make_entity(submit_id=sid_new, is_flow_completed=True, end_time=_ts(10))
        in_progress = _make_entity(submit_id=sid_ip, activity_flow_order=3, end_time=_ts(7))

        result = _make_result([old_completed, new_completed, in_progress])
        AnswerService._filter_activity_flows(result)

        assert len(result.activity_flows) == 1
        assert result.activity_flows[0].submit_id == sid_new  # in_progress(T=7) < new_completed(T=10)

    def test_multiple_in_progress_after_completion_farthest_along_wins(self):
        # when several in-progress submissions all postdate the completion, farthest wins
        sid_c = uuid.uuid4()
        sid_ip1 = uuid.uuid4()
        sid_ip2 = uuid.uuid4()
        completed = _make_entity(submit_id=sid_c, is_flow_completed=True, end_time=_ts(5))
        ip1 = _make_entity(submit_id=sid_ip1, activity_flow_order=1, end_time=_ts(10))
        ip2 = _make_entity(submit_id=sid_ip2, activity_flow_order=3, end_time=_ts(15))

        result = _make_result([completed, ip1, ip2])
        AnswerService._filter_activity_flows(result)

        assert len(result.activity_flows) == 1
        assert result.activity_flows[0].submit_id == sid_ip2
        assert result.activity_flows[0].activity_flow_order == 3
