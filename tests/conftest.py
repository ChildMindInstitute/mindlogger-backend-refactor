import uuid
from typing import AsyncGenerator, Any

import pytest
from pytest_mock import MockerFixture

#####################################################
## Shared Fixtures between unit and integration tests
#####################################################

@pytest.fixture
def local_image_name() -> str:
    return "test.jpg"

@pytest.fixture
def remote_image(local_image_name: str) -> str:
    # TODO: add support for localimages for tests
    return f"http://localhost/{local_image_name}"


@pytest.fixture
async def mock_kiq_report(mocker) -> AsyncGenerator[Any, Any]:
    mock = mocker.patch("apps.answers.service.create_report.kiq")
    yield mock


@pytest.fixture
async def mock_report_server_response(mocker) -> AsyncGenerator[Any, Any]:
    Recipients = list[str]
    FakeBody = dict[str, str | dict[str, str | Recipients]]

    def json_() -> FakeBody:
        return dict(
            pdf="cGRmIGJvZHk=",
            email=dict(
                body="Body",
                subject="Subject",
                attachment="Attachment name",
                emailRecipients=["tom@cmiml.net"],
            ),
        )

    mock = mocker.patch("aiohttp.ClientSession.post")
    mock.return_value.__aenter__.return_value.status = 200
    mock.return_value.__aenter__.return_value.json.side_effect = json_
    yield mock


@pytest.fixture
async def mock_reencrypt_kiq(mocker) -> AsyncGenerator[Any, Any]:
    mock = mocker.patch("apps.users.api.password.reencrypt_answers.kiq")
    yield mock


@pytest.fixture(autouse=True)
def mock_audit_event_kiq(mocker: MockerFixture):
    """Prevent audit events from being persisted during tests.

    ``audit.log()`` enqueues ``send_audit_event``, which the in-memory test
    broker runs synchronously. That task opens its own DB session and commits
    to ``audit_logs`` outside the test's transaction, leaking rows across tests.
    Tests that assert audit behaviour mock ``log`` directly, and the audit
    query/export tests seed ``audit_logs`` explicitly, so disabling the enqueue
    here is safe.
    """
    return mocker.patch("apps.audit.service.send_audit_event.kiq")


@pytest.fixture(scope="session")
def uuid_zero() -> uuid.UUID:
    return uuid.UUID("00000000-0000-0000-0000-000000000000")


# @pytest.fixture
# def faketime(mocker: MockerFixture) -> type[FakeTime]:
#     mock = mocker.patch("datetime.datetime", new=FakeTime)
#     return mock