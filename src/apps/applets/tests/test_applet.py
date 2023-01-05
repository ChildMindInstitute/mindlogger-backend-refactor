import pytest

from apps.shared.test import BaseTest
from infrastructure.database import transaction


class TestApplet(BaseTest):
    fixtures = [
        "users/fixtures/users.json",
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_user_accesses.json",
        "activities/fixtures/activities.json",
        "activities/fixtures/activity_items.json",
    ]

    login_url = "/auth/token"
    applet_list_url = "applets"
    applet_detail_url = "applets/{pk}"

    @transaction.rollback
    async def test_creating_applet(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        create_data = dict(
            display_name="User daily behave",
            description=dict(
                en="Understand users behave",
                fr="Comprendre le comportement des utilisateurs",
            ),
            about=dict(
                en="Understand users behave",
                fr="Comprendre le comportement des utilisateurs",
            ),
            activities=[
                dict(
                    name="Morning activity",
                    guid="577dbbda-3afc-4962-842b-8d8d11588bfe",
                    description=dict(
                        en="Understand morning feelings.",
                        fr="Understand morning feelings.",
                    ),
                    items=[
                        dict(
                            question=dict(
                                en="How had you slept?",
                                fr="How had you slept?",
                            ),
                            response_type="choices",
                            answers=["Bad", "Normal", "Good"],
                        ),
                    ],
                ),
                dict(
                    name="Evening activity",
                    guid="577dbbda-3afc-4962-842b-8d8d11588bff",
                    description=dict(
                        en="Understand evening feelings.",
                        fr="Understand evening feelings.",
                    ),
                    items=[
                        dict(
                            question=dict(
                                en="How had you spent your time?",
                                fr="How had you spent your time?",
                            ),
                            response_type="choices",
                            answers=["Bad", "Normal", "Good"],
                        ),
                    ],
                ),
            ],
            activity_flows=[
                dict(
                    name="Morning questionnaire",
                    description=dict(
                        en="Understand how was the morning",
                        fr="Understand how was the morning",
                    ),
                    items=[
                        dict(
                            activity_guid="577dbbda-3afc-"
                            "4962-842b-8d8d11588bfe"
                        )
                    ],
                )
            ],
        )
        response = await self.client.post(
            self.applet_list_url, data=create_data
        )

        assert response.status_code == 201, response.json()

    @transaction.rollback
    async def test_create_duplicate_name_applet(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        create_data = dict(
            display_name="Applet 1",
            description=dict(
                en="Understand users behave",
                fr="Comprendre le comportement des utilisateurs",
            ),
            about=dict(
                en="Understand users behave",
                fr="Comprendre le comportement des utilisateurs",
            ),
            activities=[
                dict(
                    name="Morning activity",
                    guid="577dbbda-3afc-4962-842b-8d8d11588bfe",
                    description=dict(
                        en="Understand morning feelings.",
                        fr="Understand morning feelings.",
                    ),
                    items=[
                        dict(
                            question=dict(
                                en="How had you slept?",
                                fr="How had you slept?",
                            ),
                            response_type="choices",
                            answers=["Bad", "Normal", "Good"],
                        ),
                    ],
                ),
                dict(
                    name="Evening activity",
                    guid="577dbbda-3afc-4962-842b-8d8d11588bff",
                    description=dict(
                        en="Understand evening feelings.",
                        fr="Understand evening feelings.",
                    ),
                    items=[
                        dict(
                            question=dict(
                                en="How had you spent your time?",
                                fr="How had you spent your time?",
                            ),
                            response_type="choices",
                            answers=["Bad", "Normal", "Good"],
                        ),
                    ],
                ),
            ],
            activity_flows=[
                dict(
                    name="Morning questionnaire",
                    description=dict(
                        en="Understand how was the morning",
                        fr="Understand how was the morning",
                    ),
                    items=[
                        dict(
                            activity_guid="577dbbda-3afc-"
                            "4962-842b-8d8d11588bfe"
                        )
                    ],
                )
            ],
        )
        response = await self.client.post(
            self.applet_list_url, data=create_data
        )

        assert response.status_code == 400, response.json()
        assert response.json()["messages"][0] == "Applet already exist"

    @transaction.rollback
    async def test_update_applet(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        update_data = dict(
            display_name="Applet 1",
            description=dict(
                en="Understand users behave",
                fr="Comprendre le comportement des utilisateurs",
            ),
            about=dict(
                en="Understand users behave",
                fr="Comprendre le comportement des utilisateurs",
            ),
            activities=[
                dict(
                    id=1,
                    name="Morning activity",
                    guid="577dbbda-3afc-4962-842b-8d8d11588bfe",
                    description=dict(
                        en="Understand morning feelings.",
                        fr="Understand morning feelings.",
                    ),
                    items=[
                        dict(
                            id=1,
                            question=dict(
                                en="How had you slept?",
                                fr="How had you slept?",
                            ),
                            response_type="choices",
                            answers=["Bad", "Normal", "Good"],
                        ),
                        dict(
                            question=dict(
                                en="How was your breakfast?",
                                fr="How was your breakfast?",
                            ),
                            response_type="choices",
                            answers=["Bad", "Normal", "Good"],
                        ),
                    ],
                ),
                dict(
                    name="Evening activity",
                    guid="577dbbda-3afc-4962-842b-8d8d11588bff",
                    description=dict(
                        en="Understand evening feelings.",
                        fr="Understand evening feelings.",
                    ),
                    items=[
                        dict(
                            question=dict(
                                en="How had you spent your time?",
                                fr="How had you spent your time?",
                            ),
                            response_type="choices",
                            answers=["Bad", "Normal", "Good"],
                        ),
                    ],
                ),
            ],
            activity_flows=[
                dict(
                    name="Morning questionnaire",
                    description=dict(
                        en="Understand how was the morning",
                        fr="Understand how was the morning",
                    ),
                    items=[
                        dict(
                            id=2,
                            activity_guid="577dbbda-"
                            "3afc-4962-842b-8d8d11588bfe",
                        )
                    ],
                )
            ],
        )
        response = await self.client.put(
            self.applet_detail_url.format(pk=1), data=update_data
        )

        assert response.status_code == 200, response.json()

    @transaction.rollback
    async def test_applet_list(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        response = await self.client.get(self.applet_list_url)

        assert response.status_code == 200
        assert len(response.json()["results"]) == 2
        assert response.json()["results"][0]["id"] == 1
        assert response.json()["results"][1]["id"] == 2

    @pytest.mark.main
    @transaction.rollback
    async def test_applet_detail(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        response = await self.client.get(self.applet_detail_url.format(pk=1))

        assert response.status_code == 200
        result = response.json()["result"]
        assert result["id"] == 1
        assert result["display_name"] == "Applet 1"
        # assert len(result['activities']) == 2
        # assert len(result['activity_flows']) == 0
