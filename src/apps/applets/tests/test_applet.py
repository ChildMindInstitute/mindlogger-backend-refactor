import pytest

from apps.shared.test import BaseTest
from infrastructure.database import transaction


class TestApplet(BaseTest):
    fixtures = ["users/fixtures/users.json"]

    login_url = "/auth/access-token"
    create_url = "applets/create"
    update_url = "applets/update"

    @pytest.mark.main
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
                            activity_guid="577dbbda-3afc-4962-842b-8d8d11588bfe"
                        )
                    ],
                )
            ],
        )
        response = await self.client.post(self.create_url, data=create_data)

        assert response.status_code == 201, response.json()

        update_data = dict(
            id=2,
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
                    id=2,
                    name="Morning activity",
                    guid="577dbbda-3afc-4962-842b-8d8d11588bfe",
                    description=dict(
                        en="Understand morning feelings.",
                        fr="Understand morning feelings.",
                    ),
                    items=[
                        dict(
                            id=2,
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
                    id=3,
                    name="Evening activity",
                    guid="577dbbda-3afc-4962-842b-8d8d11588bff",
                    description=dict(
                        en="Understand evening feelings.",
                        fr="Understand evening feelings.",
                    ),
                    items=[
                        dict(
                            id=3,
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
                    id=2,
                    name="Morning questionnaire",
                    description=dict(
                        en="Understand how was the morning",
                        fr="Understand how was the morning",
                    ),
                    items=[
                        dict(
                            id=2,
                            activity_guid="577dbbda-3afc-4962-842b-8d8d11588bfe",
                        )
                    ],
                )
            ],
        )
        response = await self.client.put(self.update_url, data=update_data)

        assert response.status_code == 200, response.json()
