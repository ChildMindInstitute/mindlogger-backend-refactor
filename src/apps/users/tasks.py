import json
from json import JSONDecodeError

from apps.answers.service import AnswerEncryptor, AnswerService
from apps.job.constants import JobStatus
from apps.job.service import JobService
from apps.shared.encryption import generate_dh_aes_key, generate_dh_public_key, generate_dh_user_private_key
from apps.workspaces.service.workspace import WorkspaceService
from broker import broker
from config import settings
from infrastructure.database import atomic, session_manager
from infrastructure.logger import logger


@broker.task
async def reencrypt_answers(
    user_id,
    email,
    old_password,
    new_password,
    retries: int | None = None,
    retry_timeout: int = settings.task_answer_encryption.retry_timeout,
):
    job_name = "reencrypt_answers"
    logger.info(f"Reencryption {user_id}: reencrypt_answers start")

    old_private_key = generate_dh_user_private_key(user_id, email, old_password)
    new_private_key = generate_dh_user_private_key(user_id, email, new_password)

    batch_limit = settings.task_answer_encryption.batch_limit
    success = True

    default_session_maker = session_manager.get_session()
    async with default_session_maker() as session:
        job_service = JobService(session, user_id)
        async with atomic(session):
            job = await job_service.get_or_create_owned(job_name, JobStatus.in_progress)
            if job.status != JobStatus.in_progress:
                await job_service.change_status(job.id, JobStatus.in_progress)

        db_applets = await WorkspaceService(session, user_id).get_user_answer_db_info()

    for db_applet_data in db_applets:
        session_maker = default_session_maker
        if arb_uri := db_applet_data.database_uri:
            session_maker = session_manager.get_session(arb_uri)

        for applet in db_applet_data.applets:
            try:
                prime = json.loads(applet.encryption.prime)
                base = json.loads(applet.encryption.base)
                applet_pub_key = json.loads(applet.encryption.public_key)
            except JSONDecodeError as e:
                logger.error(f"Reencryption {user_id}: Wrong applet {applet.applet_id} encryption format, skip")
                logger.exception(str(e))
                continue

            old_public_key = generate_dh_public_key(old_private_key, prime, base)
            new_public_key = generate_dh_public_key(new_private_key, prime, base)
            old_aes_key = generate_dh_aes_key(old_private_key, applet_pub_key, prime)
            new_aes_key = generate_dh_aes_key(new_private_key, applet_pub_key, prime)

            page = 1
            try:
                while True:
                    async with session_maker() as session:
                        async with atomic(session):
                            service = AnswerService(session)
                            count = await service.reencrypt_user_answers(
                                applet.applet_id,
                                user_id,
                                page=page,
                                limit=batch_limit,
                                old_public_key=old_public_key,
                                new_public_key=new_public_key,
                                encryptor=AnswerEncryptor(bytes(new_aes_key)),
                                decryptor=AnswerEncryptor(bytes(old_aes_key)),
                            )
                            if count < batch_limit:
                                break
                            page += 1

            except Exception as e:
                msg = f"Reencryption {user_id}: cannot process applet {applet.applet_id}, skip"
                logger.error(msg)
                logger.exception(str(e))
                async with default_session_maker() as session:
                    async with atomic(session):
                        details = dict(errors=[msg, str(e)])
                        await JobService(session, user_id).change_status(job.id, JobStatus.error, details)
                success = False
                continue

    # Update job status, schedule retry
    async with default_session_maker() as session:
        async with atomic(session):
            if success:
                await JobService(session, user_id).change_status(job.id, JobStatus.success)
            else:
                if retries:
                    await JobService(session, user_id).change_status(job.id, JobStatus.retry)

                    logger.info(f"Reencryption {user_id}: schedule retry")
                    retries -= 1
                    await (
                        reencrypt_answers.kicker()
                        .with_labels(delay=retry_timeout)
                        .kiq(
                            user_id,
                            email,
                            old_password,
                            new_password,
                            retries=retries,
                            retry_timeout=retry_timeout,
                        )
                    )
