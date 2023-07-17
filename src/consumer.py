import asyncio
import base64
import datetime
import io
import json
import logging
from pprint import pprint

import aio_pika
from fastapi import UploadFile

from apps.answers.service import ReportServerService
from apps.mailing.domain import MessageSchema
from apps.mailing.services import MailingService
from infrastructure.database import session_manager
from infrastructure.utility.rabbitmq_queue import RabbitMqQueue

logger = logging.getLogger("mindlogger_backend")


async def create_report(message: aio_pika.abc.AbstractIncomingMessage):
    data = json.loads(message.body.decode())
    logger.info(
        f"---Received message at {datetime.datetime.now().isoformat()}---"
    )
    pprint(data)
    session_maker = session_manager.get_session()
    mail_service = MailingService()
    async with session_maker() as session:
        service = ReportServerService(session)
        response = await service.create_report(**data)
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
