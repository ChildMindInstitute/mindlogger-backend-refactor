import asyncio
import base64
import datetime
import io
import json
import logging
import traceback
from pprint import pprint

import aio_pika
import sentry_sdk
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from apps.answers.deps.preprocess_arbitrary import get_arbitrary_info
from apps.answers.domain import ReportServerResponse
from apps.answers.service import ReportServerService
from apps.mailing.domain import MessageSchema
from apps.mailing.services import MailingService
from infrastructure.database import session_manager
from infrastructure.utility.rabbitmq_queue import RabbitMqQueue

logger = logging.getLogger("mindlogger_backend")


async def _create_report(
    data: dict,
    session: AsyncSession,
    arbitrary_session: AsyncSession | None = None,
) -> ReportServerResponse | None:
    service = ReportServerService(session, arbitrary_session=arbitrary_session)
    return await service.create_report(**data)


async def create_report(message: aio_pika.abc.AbstractIncomingMessage):
    async with message.process():
        logger.info(
            f"---Received message at {datetime.datetime.now().isoformat()}---"
        )
        try:
            data = json.loads(message.body.decode())
            pprint(data)
            applet_id = data.pop("applet_id")
            session_maker = session_manager.get_session()
            mail_service = MailingService()

            async with session_maker() as session:
                arb_uri = await get_arbitrary_info(applet_id, session)
                if arb_uri:
                    arb_session_maker = session_manager.get_session(arb_uri)
                    async with arb_session_maker() as arb_session:
                        response = await _create_report(
                            data, session, arb_session
                        )
                else:
                    response = await _create_report(data, session)

                if not response:
                    return
                file = UploadFile(
                    response.email.attachment,
                    io.BytesIO(base64.b64decode(response.pdf.encode())),
                    "application/pdf",
                )
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


async def main():
    logger.info("---Creating app---")
    queue = RabbitMqQueue()
    await queue.connect()
    logger.info("---Successfully connected to rabbitmq---")
    await queue.consume(callback=create_report)
    logger.info("---Successfully started consuming---")
    try:
        await asyncio.Future()
    finally:
        await queue.close()


if __name__ == "__main__":
    asyncio.run(main())
