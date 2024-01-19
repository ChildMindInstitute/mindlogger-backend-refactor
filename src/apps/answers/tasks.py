import base64
import io
import traceback
import uuid

import sentry_sdk
from fastapi import UploadFile
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession

from apps.answers.crud.answers import AnswersCRUD
from apps.answers.deps.preprocess_arbitrary import get_arbitrary_info
from apps.answers.domain import ReportServerResponse
from apps.applets.crud import AppletsCRUD
from apps.mailing.domain import MessageSchema
from apps.mailing.services import MailingService
from apps.workspaces.domain.constants import DataRetention
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
                try:
                    async with arb_session_maker() as arb_session:
                        response = await _create_report(
                            submit_id, answer_id, session, arb_session
                        )
                finally:
                    await arb_session_maker.remove()
            else:
                response = await _create_report(submit_id, answer_id, session)

            if not response:
                return
            file = UploadFile(
                response.email.attachment,
                io.BytesIO(base64.b64decode(response.pdf.encode())),
                "application/pdf",
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
    finally:
        if not isinstance(session_maker, AsyncSession):
            await session_maker.remove()


@broker.task(
    task_name="apps.answers.tasks:removing_outdated_answers",
    schedule=[{"cron": "*/30 * * * *"}],
)
async def removing_outdated_answers():
    session_maker = session_manager.get_session()
    try:
        async with session_maker() as session:
            applets_data: Result = await AppletsCRUD(
                session
            ).get_every_non_indefinitely_applet_retentions()
            for applet_data in applets_data:
                applet_id, retention_period, retention_type = applet_data
                retention_type = DataRetention(retention_type)

                arb_uri = await get_arbitrary_info(applet_id, session)
                if arb_uri:
                    arb_session_maker = session_manager.get_session(arb_uri)
                    try:
                        async with arb_session_maker() as arb_session:
                            await AnswersCRUD(
                                arb_session
                            ).removing_outdated_answers(
                                applet_id, retention_period, retention_type
                            )
                    finally:
                        await arb_session_maker.remove()
                else:
                    await AnswersCRUD(session).removing_outdated_answers(
                        applet_id, retention_period, retention_type
                    )
            await session.commit()
    except Exception as e:
        traceback.print_exception(e)
        sentry_sdk.capture_exception(e)
    finally:
        if not isinstance(session_maker, AsyncSession):
            await session_maker.remove()
