import uuid

from apps.answers.domain import AppletAnswerCreate


class AlertService:
    def __init__(self, session, user_id: uuid.UUID):
        self.user_id = user_id
        self.session = session

    async def create_alert(self, applet_answer: AppletAnswerCreate):
        pass
        # schemas = list()
        # for answer in applet_answer.answers:
        #     activity_item_id_version = (
        #         f"{answer.activity_item_id}_{applet_answer.version}"
        #     )
        #     flow_id_version = None
        #     if answer.flow_id:
        #         flow_id_version = (
        #             f"{applet_answer.}_{applet_answer.version}"
        #         )
        #     schemas = await AnswerItemsCRUD(
        #         self.session
        #     ).get_for_answers_created(
        #         self.user_id,
        #         applet_answer,
        #         activity_item_id_version,
        #         flow_id_version,
        #     )
        #
        #
        # for schema in schemas:
        #     try:
        #         alert_config = await AlertConfigsCRUD(
        #             self.session
        #         ).get_by_applet_item_answer(
        #             AlertConfigGet(
        #                 applet_id=schema.applet_id,
        #                 activity_item_histories_id_version=(
        #                     schema.activity_item_history_id
        #                 ),
        #                 specific_answer=json.loads(schema.answer)["value"],
        #             )
        #         )
        #     except AlertConfigNotFoundError:
        #         continue
        #
        #     if alert_config:
        #         await AlertCRUD(self.session).save(
        #             AlertCreate(
        #                 specific_answer=schema.answer,
        #                 respondent_id=schema.respondent_id,
        #                 alert_config_id=alert_config.id,
        #                 applet_id=schema.applet_id,
        #                 alert_message=alert_config.alert_message,
        #                 activity_item_histories_id_version=(
        #                     schema.activity_item_history_id
        #                 ),
        #             )
        #         )
