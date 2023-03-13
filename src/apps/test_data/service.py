import uuid

from apps.activities.domain.activity_create import ActivityItemCreate
from apps.activities.domain.response_type_config import ResponseType, TextConfig, ChoiceConfig
from apps.applets.domain.applet_create import AppletCreate
from apps.applets.service import AppletService
import string
import random


class TestDataService:
    def __init__(self, user_id: uuid.UUID):
        self.user_id = user_id

    async def create_applet(self):
        applet = await AppletService(self.user_id).create(applet_create)
        return applet

    @staticmethod
    def random_string(length=10):
        letters = string.ascii_letters + ' '
        return ''.join(random.choice(letters) for _ in range(length))

    def _generate_applet(self) -> AppletCreate:
        applet_create = AppletCreate(
            display_name=self.random_string(),
            description=self.random_string(50),
            about=self.random_string(50),
            image=self.random_string(),
            watermark=self.random_string(),
            theme_id="",
            report_server_ip="",
            report_public_key="",
            report_recipients=[],
            report_include_user_id=False,
            report_include_case_id=False,
            report_email_body="",
            activities=[],
            activity_flows=[]
        )

        return applet_create

    def _generate_activities(self, count=10):
        for _ in range(count):
            items = None

    def _generate_activity_items(self, count=10) -> list[ActivityItemCreate]:
        items = []
        for _ in range(count):
            items.append(ActivityItemCreate(
                header_image=None,
                question=None,
                response_type=None,
                answers=None,
                config=None,
                skippable_item=None,
                remove_availability_to_go_back=None,
            ))
        return items

    def _generate_response_type(self, type_: ResponseType):
        if type_ == ResponseType.TEXT:
            return TextConfig(

            )
        elif type_ == ResponseType.CHOICE:
            return ChoiceConfig(

            )
