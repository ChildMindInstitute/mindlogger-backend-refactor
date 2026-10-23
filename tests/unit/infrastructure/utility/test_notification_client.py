import uuid

from pytest_mock import MockerFixture

from infrastructure.utility.notification_client import FCMNotification, FirebaseMessage, FirebaseNotificationType


async def test_notify_sends_tokens_in_batches_of_500(mocker: MockerFixture):
    send = mocker.patch("firebase_admin.messaging.send_each_for_multicast")
    # FCMNotification() returns the test stub in testing env, so build the real client directly
    client = object.__new__(FCMNotification)
    client._initialized = True
    devices = [f"token-{i}" for i in range(1200)]
    message = FirebaseMessage(
        title="Applet is updated.",
        body="Applet is updated.",
        data=dict(type=FirebaseNotificationType.APPLET_UPDATE, applet_id=uuid.uuid4()),
    )

    await client.notify(devices, message)

    sent = [call.args[0].tokens for call in send.call_args_list]
    assert [len(tokens) for tokens in sent] == [500, 500, 200]
    assert sorted(token for tokens in sent for token in tokens) == sorted(devices)
