import json
from json import JSONDecodeError

from apps.answers.service import AnswerEncryptor, AnswerService
from apps.shared.encryption import (
    generate_dh_public_key,
    generate_dh_user_private_key,
    geterate_dh_aes_key,
)
from apps.workspaces.service.workspace import WorkspaceService
from broker import broker
from config import settings
from infrastructure.database import atomic, session_manager
from infrastructure.logger import logger


@broker.task
async def change_password_with_answers(
    user_id,
    email,
    old_password,
    new_password,
):
    old_private_key = generate_dh_user_private_key(
        user_id, email, old_password
    )
    new_private_key = generate_dh_user_private_key(
        user_id, email, new_password
    )

    batch_limit = settings.task_answer_encryption.batch_limit
    success = True

    default_session_maker = session_manager.get_session()
    try:
        async with default_session_maker() as session:
            db_applets = await WorkspaceService(
                session, user_id
            ).get_user_answer_db_info()
    finally:
        await default_session_maker.remove()

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
                logger.error(
                    f'Reencryption: Wrong applet "{applet.applet_id}" encryption format, skip'  # noqa: E501
                )
                logger.exception(str(e))
                continue

            old_public_key = generate_dh_public_key(
                old_private_key, prime, base
            )
            new_public_key = generate_dh_public_key(
                new_private_key, prime, base
            )
            old_aes_key = geterate_dh_aes_key(
                old_private_key, applet_pub_key, prime
            )
            new_aes_key = geterate_dh_aes_key(
                new_private_key, applet_pub_key, prime
            )

            page = 1
            try:
                while True:
                    try:
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
                                    encryptor=AnswerEncryptor(
                                        bytes(new_aes_key)
                                    ),
                                    decryptor=AnswerEncryptor(
                                        bytes(old_aes_key)
                                    ),
                                )
                                if count < batch_limit:
                                    break
                                page += 1
                    finally:
                        await session_maker.remove()

            except Exception as e:
                logger.error(f"Reencryption: {e}")
                logger.exception(str(e))
                success = False
                continue

    if not success:
        # TODO retry
        ...
