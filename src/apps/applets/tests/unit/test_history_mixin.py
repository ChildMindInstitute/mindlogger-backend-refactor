import uuid

import pytest

from apps.applets.db.schemas.applet import HistoryAware


def test_history_mixin_generate_id_version():
    id_ = uuid.uuid4()
    version = "0.0.0"
    result = HistoryAware.generate_id_version(id_, version)
    assert result == f"{id_}_{version}"


def test_history_mixin_split_version_id():
    id_ = uuid.uuid4()
    version = "0.0.0"
    id_version = HistoryAware.generate_id_version(id_, version)
    split_id, split_version = HistoryAware.split_id_version(id_version)
    assert split_id == id_
    assert split_version == version


@pytest.mark.parametrize(
    "wrong_id_version,error",
    (
        (str(uuid.uuid4()), Exception),
        (f"{uuid.uuid4()}_0.0.0_1.0.0", Exception),
        ("not_uuid", ValueError),
    ),
)
def test_history_mixin_split_version_id__wrong_id_version(wrong_id_version: str, error: Exception):
    # NOTE: ideally we should raise a custom error not Exception
    with pytest.raises(error):  # type: ignore[call-overload]
        HistoryAware.split_id_version(wrong_id_version)
