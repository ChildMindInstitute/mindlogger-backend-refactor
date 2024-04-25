import base64
import io
import traceback
import uuid

import sentry_sdk
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from apps.answers.deps.preprocess_arbitrary import get_arbitrary_info
from apps.answers.domain import ReportServerResponse
from apps.mailing.domain import MessageSchema
from apps.mailing.services import MailingService
from broker import broker
from infrastructure.database import session_manager

# moved from previous implementation


async def _create_report(
    submit_id: uuid.UUID,
    answer_id: uuid.UUID | None,
    session: AsyncSession,
    arbitrary_session: AsyncSession | None = None,
) -> ReportServerResponse | None:
    from apps.answers.service import ReportServerService

    service = ReportServerService(session, arbitrary_session=arbitrary_session)

    return await service.create_report(submit_id, answer_id)


@broker.task()
async def create_report(
    applet_id: uuid.UUID,
    submit_id: uuid.UUID,
    answer_id: uuid.UUID | None = None,
):
    session_maker = session_manager.get_session()
    try:
        async with session_maker() as session:
            arb_uri = await get_arbitrary_info(applet_id, session)
            if arb_uri:
                arb_session_maker = session_manager.get_session(arb_uri)
                async with arb_session_maker() as arb_session:
                    response = await _create_report(submit_id, answer_id, session, arb_session)
            else:
                response = await _create_report(submit_id, answer_id, session)

            if not response:
                return
            file = UploadFile(
                io.BytesIO(base64.b64decode(response.pdf.encode())),
                filename=response.email.attachment,
            )

            mail_service = MailingService()
            await mail_service.send(
                MessageSchema(
                    recipients=response.email.email_recipients,
                    subject=response.email.subject,
                    body=response.email.body,
                    attachments=[file],
                )
            )
    except Exception as e:
        traceback.print_exception(e)
        sentry_sdk.capture_exception(e)
