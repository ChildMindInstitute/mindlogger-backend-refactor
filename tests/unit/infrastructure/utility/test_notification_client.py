import uuid

import pytest
from pytest_mock import MockerFixture

from config import settings
from infrastructure.utility.notification_client import FCMNotification, FirebaseMessage, FirebaseNotificationType


@pytest.mark.parametrize(
    "batch_size,total,expected",
    (
        (500, 1200, [500, 500, 200]),
        (1, 3, [1, 1, 1]),
    ),
)
async def test_notify_sends_tokens_in_batches(mocker: MockerFixture, batch_size: int, total: int, expected: list[int]):
    mocker.patch.object(settings.fcm, "multicast_batch_size", batch_size)
    send = mocker.patch("firebase_admin.messaging.send_each_for_multicast")
    # FCMNotification() returns the test stub in testing env, so build the real client directly
    client = object.__new__(FCMNotification)
    client._initialized = True
    devices = [f"token-{i}" for i in range(total)]
    message = FirebaseMessage(
        title="Applet is updated.",
        body="Applet is updated.",
        data=dict(type=FirebaseNotificationType.APPLET_UPDATE, applet_id=uuid.uuid4()),
    )

    await client.notify(devices, message)

    sent = [call.args[0].tokens for call in send.call_args_list]
    assert [len(tokens) for tokens in sent] == expected
    assert sorted(token for tokens in sent for token in tokens) == sorted(devices)


async def test_notify_fails_when_batch_is_over_test_token_limit(mocker: MockerFixture):
    mocker.patch.object(settings.fcm, "test_token_limit", 2)
    mocker.patch.object(settings.fcm, "multicast_batch_size", 3)
    send = mocker.patch("firebase_admin.messaging.send_each_for_multicast")
    client = object.__new__(FCMNotification)
    client._initialized = True
    message = FirebaseMessage(
        title="Applet is updated.",
        body="Applet is updated.",
        data=dict(type=FirebaseNotificationType.APPLET_UPDATE, applet_id=uuid.uuid4()),
    )

    with pytest.raises(ValueError, match="more than 2 tokens"):
        await client.notify(["token-1", "token-2", "token-3"], message)
    send.assert_not_called()
