import asyncio

from apps.shared.test import BaseTest
from infrastructure.database import rollback


class TestApplet(BaseTest):
    # TODO: fix text
    fixtures = [
        "users/fixtures/users.json",
        "themes/fixtures/themes.json",
        "folders/fixtures/folders.json",
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_user_accesses.json",
        "activities/fixtures/activities.json",
        "activities/fixtures/activity_items.json",
        "activity_flows/fixtures/activity_flows.json",
        "activity_flows/fixtures/activity_flow_items.json",
    ]

    login_url = "/auth/login"
    applet_list_url = "applets"
    applet_detail_url = f"{applet_list_url}/{{pk}}"
    applet_unique_name_url = f"{applet_list_url}/unique_name"
    histories_url = f"{applet_detail_url}/versions"
    history_url = f"{applet_detail_url}/versions/{{version}}"
    history_changes_url = f"{applet_detail_url}/versions/{{version}}/changes"

    @rollback
    async def test_creating_applet(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        create_data = dict(
            password="Test1234!",
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
                    key="577dbbda-3afc-4962-842b-8d8d11588bfe",
                    description=dict(
                        en="Understand morning feelings.",
                        fr="Understand morning feelings.",
                    ),
                    items=[
                        dict(
                            name="morning_activity_item",
                            question=dict(
                                en="How had you slept?",
                                fr="How had you slept?",
                            ),
                            response_type="text",
                            response_values=None,
                            config=dict(
                                max_response_length=200,
                                correct_answer_required=False,
                                correct_answer=None,
                                numerical_response_required=False,
                                response_data_identifier=False,
                                response_required=False,
                                remove_back_button=False,
                                skippable_item=True,
                            ),
                        ),
                        dict(
                            name="morning_activity_item_2",
                            question=dict(
                                en="How had you woke?",
                                fr="How had you woke?",
                            ),
                            response_type="slider",
                            response_values=dict(
                                min_label="Not at all",
                                max_label="Very much",
                                min_value=1,
                                max_value=5,
                                min_image=None,
                                max_image=None,
                                scores=None,
                            ),
                            config=dict(
                                add_scores=False,
                                set_alerts=False,
                                show_tick_marks=False,
                                show_tick_labels=False,
                                continuous_slider=False,
                                timer=None,
                                remove_back_button=False,
                                skippable_item=True,
                                additional_response_option=dict(
                                    text_input_option=False,
                                    text_input_required=False,
                                ),
                            ),
                        ),
                    ],
                ),
                dict(
                    name="Evening activity",
                    key="577dbbda-3afc-4962-842b-8d8d11588bff",
                    description=dict(
                        en="Understand evening feelings.",
                        fr="Understand evening feelings.",
                    ),
                    items=[
                        dict(
                            name="evening_activity_item",
                            question=dict(
                                en="How had you slept?",
                                fr="How had you slept?",
                            ),
                            response_type="singleSelect",
                            response_values=dict(
                                options=[
                                    dict(
                                        # id="41dfea7e-4496-42b3-ab24-3dd7cce71312",
                                        text="Very well",
                                        image=None,
                                        score=None,
                                        tooltip=None,
                                        is_hidden=False,
                                        color=None,
                                    ),
                                    dict(
                                        # id="41dfea7e-4496-42b3-ab24-3dd7cce71313",
                                        text="Well",
                                        image=None,
                                        score=None,
                                        tooltip=None,
                                        is_hidden=False,
                                        color=None,
                                    ),
                                ]
                            ),
                            config=dict(
                                remove_back_button=False,
                                skippable_item=True,
                                randomize_options=False,
                                timer=None,
                                add_scores=False,
                                set_alerts=False,
                                add_tooltip=False,
                                set_palette=False,
                                additional_response_option=dict(
                                    text_input_option=False,
                                    text_input_required=False,
                                ),
                            ),
                        ),
                        dict(
                            name="evening_activity_item",
                            question=dict(
                                en="How had you slept?",
                                fr="How had you slept?",
                            ),
                            response_type="multiSelect",
                            response_values=dict(
                                options=[
                                    dict(
                                        # id="41dfea7e-4496-42b3-ab24-3dd7cce71312",
                                        text="Very well",
                                        image=None,
                                        score=None,
                                        tooltip=None,
                                        is_hidden=False,
                                        color=None,
                                    ),
                                    dict(
                                        # id="41dfea7e-4496-42b3-ab24-3dd7cce71313",
                                        text="Well",
                                        image=None,
                                        score=None,
                                        tooltip=None,
                                        is_hidden=False,
                                        color=None,
                                    ),
                                ]
                            ),
                            config=dict(
                                remove_back_button=False,
                                skippable_item=True,
                                randomize_options=False,
                                timer=None,
                                add_scores=False,
                                set_alerts=False,
                                add_tooltip=False,
                                set_palette=False,
                                additional_response_option=dict(
                                    text_input_option=False,
                                    text_input_required=False,
                                ),
                            ),
                        ),
                        dict(
                            name="evening_activity_item33",
                            question=dict(
                                en="How had you slept?",
                                fr="How had you slept?",
                            ),
                            response_type="photo",
                            response_values=None,
                            config=dict(
                                remove_back_button=False,
                                skippable_item=True,
                                timer=None,
                                additional_response_option=dict(
                                    text_input_option=False,
                                    text_input_required=False,
                                ),
                            ),
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
                            activity_key="577dbbda-3afc-"
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

    @rollback
    async def test_create_duplicate_name_applet(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        create_data = dict(
            password="Test1234!",
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
                    key="577dbbda-3afc-4962-842b-8d8d11588bfe",
                    description=dict(
                        en="Understand morning feelings.",
                        fr="Understand morning feelings.",
                    ),
                    items=[
                        dict(
                            name="evening_activity_item",
                            question=dict(
                                en="How had you slept?",
                                fr="How had you slept?",
                            ),
                            response_type="text",
                            response_values=None,
                            config=dict(
                                max_response_length=200,
                                correct_answer_required=False,
                                correct_answer=None,
                                numerical_response_required=False,
                                response_data_identifier=False,
                                response_required=False,
                                remove_back_button=False,
                                skippable_item=True,
                            ),
                        ),
                    ],
                ),
                dict(
                    name="Evening activity",
                    key="577dbbda-3afc-4962-842b-8d8d11588bff",
                    description=dict(
                        en="Understand evening feelings.",
                        fr="Understand evening feelings.",
                    ),
                    items=[
                        dict(
                            name="evening_activity_item",
                            question=dict(
                                en="How had you slept?",
                                fr="How had you slept?",
                            ),
                            response_type="text",
                            response_values=None,
                            config=dict(
                                max_response_length=200,
                                correct_answer_required=False,
                                correct_answer=None,
                                numerical_response_required=False,
                                response_data_identifier=False,
                                response_required=False,
                                remove_back_button=False,
                                skippable_item=True,
                            ),
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
                            activity_key="577dbbda-3afc-"
                            "4962-842b-8d8d11588bfe"
                        )
                    ],
                )
            ],
        )
        response = await self.client.post(
            self.applet_list_url, data=create_data
        )
        assert response.status_code == 422, response.json()
        assert (
            response.json()["result"][0]["message"]["en"]
            == "Applet already exists."
        )

    @rollback
    async def test_update_applet(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        update_data = dict(
            password="Test1234!",
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
                    id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
                    name="Morning activity",
                    key="577dbbda-3afc-4962-842b-8d8d11588bfe",
                    description=dict(
                        en="Understand morning feelings.",
                        fr="Understand morning feelings.",
                    ),
                    items=[
                        dict(
                            id="a18d3409-2c96-4a5e-a1f3-1c1c14be0011",
                            name="evening_activity_item",
                            question=dict(
                                en="How had you slept?",
                                fr="How had you slept?",
                            ),
                            response_type="text",
                            response_values=None,
                            config=dict(
                                max_response_length=200,
                                correct_answer_required=False,
                                correct_answer=None,
                                numerical_response_required=False,
                                response_data_identifier=False,
                                response_required=False,
                                remove_back_button=False,
                                skippable_item=True,
                            ),
                        ),
                        dict(
                            name="evening_activity_item2",
                            question=dict(
                                en="How was your breakfast?",
                                fr="How was your breakfast?",
                            ),
                            response_type="text",
                            response_values=None,
                            config=dict(
                                max_response_length=200,
                                correct_answer_required=False,
                                correct_answer=None,
                                numerical_response_required=False,
                                response_data_identifier=False,
                                response_required=False,
                                remove_back_button=False,
                                skippable_item=True,
                            ),
                        ),
                    ],
                ),
                dict(
                    name="Evening activity",
                    key="577dbbda-3afc-4962-842b-8d8d11588bff",
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
                            name="evening_activity_item3",
                            response_type="text",
                            response_values=None,
                            config=dict(
                                max_response_length=200,
                                correct_answer_required=False,
                                correct_answer=None,
                                numerical_response_required=False,
                                response_data_identifier=False,
                                response_required=False,
                                remove_back_button=False,
                                skippable_item=True,
                            ),
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
                            id="7941b770-b649-42fc-832a-870e11bdd402",
                            activity_key="577dbbda-"
                            "3afc-4962-842b-8d8d11588bfe",
                        )
                    ],
                )
            ],
        )
        response = await self.client.put(
            self.applet_detail_url.format(
                pk="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=update_data,
        )
        assert response.status_code == 200, response.json()

    @rollback
    async def test_applet_list(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        response = await self.client.get(self.applet_list_url)

        assert response.status_code == 200, response.json()
        assert len(response.json()["result"]) == 3
        assert (
            response.json()["result"][0]["id"]
            == "92917a56-d586-4613-b7aa-991f2c4b15b4"
        )
        assert (
            response.json()["result"][1]["id"]
            == "92917a56-d586-4613-b7aa-991f2c4b15b2"
        )
        assert (
            response.json()["result"][2]["id"]
            == "92917a56-d586-4613-b7aa-991f2c4b15b1"
        )

    @rollback
    async def test_applet_list_with_invalid_token(self):
        from config import settings

        settings.authentication.access_token.expiration = 0.05
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        await asyncio.sleep(4)
        response = await self.client.get(self.applet_list_url)

        assert response.status_code == 401, response.json()

    @rollback
    async def test_applet_list_with_expired_token(self):
        response = await self.client.get(
            self.applet_list_url,
            headers=dict(Authorization="Bearer invalid_token"),
        )

        assert response.status_code == 401, response.json()

    @rollback
    async def test_applet_list_by_filters(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        response = await self.client.get(
            self.applet_list_url, dict(ordering="id", owner_id=1, limit=1)
        )

        assert response.status_code == 200
        assert len(response.json()["result"]) == 1
        assert (
            response.json()["result"][0]["id"]
            == "92917a56-d586-4613-b7aa-991f2c4b15b1"
        )

    @rollback
    async def test_applet_detail(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        response = await self.client.get(
            self.applet_detail_url.format(
                pk="92917a56-d586-4613-b7aa-991f2c4b15b1"
            )
        )
        assert response.status_code == 200
        result = response.json()["result"]
        assert result["id"] == "92917a56-d586-4613-b7aa-991f2c4b15b1"
        assert result["displayName"] == "Applet 1"
        assert len(result["activities"]) == 1
        assert len(result["activityFlows"]) == 2
        assert len(result["activityFlows"][0]["activityIds"]) == 1
        assert len(result["activityFlows"][1]["activityIds"]) == 1

    @rollback
    async def test_creating_applet_history(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        create_data = dict(
            password="Test1234!",
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
                    key="577dbbda-3afc-4962-842b-8d8d11588bfe",
                    description=dict(
                        en="Understand morning feelings.",
                        fr="Understand morning feelings.",
                    ),
                    items=[
                        dict(
                            name="morning_activity_item1",
                            question=dict(
                                en="How had you slept?",
                                fr="How had you slept?",
                            ),
                            response_type="text",
                            response_values=None,
                            config=dict(
                                max_response_length=200,
                                correct_answer_required=False,
                                correct_answer=None,
                                numerical_response_required=False,
                                response_data_identifier=False,
                                response_required=False,
                                remove_back_button=False,
                                skippable_item=True,
                            ),
                        ),
                    ],
                ),
                dict(
                    name="Evening activity",
                    key="577dbbda-3afc-4962-842b-8d8d11588bff",
                    description=dict(
                        en="Understand evening feelings.",
                        fr="Understand evening feelings.",
                    ),
                    items=[
                        dict(
                            name="evening_activity_item1",
                            question=dict(
                                en="How had you spent your time?",
                                fr="How had you spent your time?",
                            ),
                            response_type="text",
                            response_values=None,
                            config=dict(
                                max_response_length=200,
                                correct_answer_required=False,
                                correct_answer=None,
                                numerical_response_required=False,
                                response_data_identifier=False,
                                response_required=False,
                                remove_back_button=False,
                                skippable_item=True,
                            ),
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
                            activity_key="577dbbda-3afc-"
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

        version = response.json()["result"]["version"]
        applet_id = response.json()["result"]["id"]

        response = await self.client.get(
            self.histories_url.format(pk=applet_id)
        )

        assert response.status_code == 200, response.json()
        versions = response.json()["result"]
        assert len(versions) == 1
        assert versions[0]["version"] == version

    @rollback
    async def test_updating_applet_history(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        update_data = dict(
            password="Test1234!",
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
                    id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
                    name="Morning activity",
                    key="577dbbda-3afc-4962-842b-8d8d11588bfe",
                    description=dict(
                        en="Understand morning feelings.",
                        fr="Understand morning feelings.",
                    ),
                    items=[
                        dict(
                            id="a18d3409-2c96-4a5e-a1f3-1c1c14be0011",
                            name="morning_activity_item132",
                            question=dict(
                                en="How had you slept?",
                                fr="How had you slept?",
                            ),
                            response_type="text",
                            response_values=None,
                            config=dict(
                                max_response_length=200,
                                correct_answer_required=False,
                                correct_answer=None,
                                numerical_response_required=False,
                                response_data_identifier=False,
                                response_required=False,
                                remove_back_button=False,
                                skippable_item=True,
                            ),
                        ),
                        dict(
                            name="morning_activity_item133",
                            question=dict(
                                en="How was your breakfast?",
                                fr="How was your breakfast?",
                            ),
                            response_type="text",
                            response_values=None,
                            config=dict(
                                max_response_length=200,
                                correct_answer_required=False,
                                correct_answer=None,
                                numerical_response_required=False,
                                response_data_identifier=False,
                                response_required=False,
                                remove_back_button=False,
                                skippable_item=True,
                            ),
                        ),
                    ],
                ),
                dict(
                    name="Evening activity",
                    key="577dbbda-3afc-4962-842b-8d8d11588bff",
                    description=dict(
                        en="Understand evening feelings.",
                        fr="Understand evening feelings.",
                    ),
                    items=[
                        dict(
                            name="evening_activity_item132",
                            question=dict(
                                en="How had you spent your time?",
                                fr="How had you spent your time?",
                            ),
                            response_type="text",
                            response_values=None,
                            config=dict(
                                max_response_length=200,
                                correct_answer_required=False,
                                correct_answer=None,
                                numerical_response_required=False,
                                response_data_identifier=False,
                                response_required=False,
                                remove_back_button=False,
                                skippable_item=True,
                            ),
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
                            id="7941b770-b649-42fc-832a-870e11bdd402",
                            activity_key="577dbbda-"
                            "3afc-4962-842b-8d8d11588bfe",
                        )
                    ],
                )
            ],
        )
        response = await self.client.put(
            self.applet_detail_url.format(
                pk="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=update_data,
        )
        assert response.status_code == 200, response.json()

        version = response.json()["result"]["version"]
        applet_id = response.json()["result"]["id"]

        response = await self.client.get(
            self.histories_url.format(pk=applet_id)
        )

        assert response.status_code == 200, response.json()
        versions = response.json()["result"]
        assert len(versions) == 1
        assert versions[0]["version"] == "1.0.1"

        response = await self.client.get(
            self.history_url.format(pk=applet_id, version=version)
        )

        assert response.status_code == 200, response.json()
        applet = response.json()["result"]
        assert applet["version"] == version

    @rollback
    async def test_history_changes(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        create_data = dict(
            password="Test1234!",
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
                    key="577dbbda-3afc-4962-842b-8d8d11588bfe",
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
                            name="morning_activity_item132",
                            response_type="text",
                            response_values=None,
                            config=dict(
                                max_response_length=200,
                                correct_answer_required=False,
                                correct_answer=None,
                                numerical_response_required=False,
                                response_data_identifier=False,
                                response_required=False,
                                remove_back_button=False,
                                skippable_item=True,
                            ),
                        ),
                    ],
                ),
                dict(
                    name="Evening activity",
                    key="577dbbda-3afc-4962-842b-8d8d11588bff",
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
                            name="evening_activity_item132",
                            response_type="text",
                            response_values=None,
                            config=dict(
                                max_response_length=200,
                                correct_answer_required=False,
                                correct_answer=None,
                                numerical_response_required=False,
                                response_data_identifier=False,
                                response_required=False,
                                remove_back_button=False,
                                skippable_item=True,
                            ),
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
                            activity_key="577dbbda-3afc-"
                            "4962-842b-8d8d11588bfe"
                        )
                    ],
                )
            ],
        )
        response = await self.client.post(
            self.applet_list_url, data=create_data
        )

        update_data = dict(
            password="Test1234!",
            display_name="User daily behave updated",
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
                    id="09e3dbf0-aefb-4d0e-9177-bdb321bf3615",
                    name="Morning activity new",
                    key="577dbbda-3afc-4962-842b-8d8d11588bfe",
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
                            name="morning_activity_item132",
                            response_type="text",
                            response_values=None,
                            config=dict(
                                max_response_length=200,
                                correct_answer_required=False,
                                correct_answer=None,
                                numerical_response_required=False,
                                response_data_identifier=False,
                                response_required=False,
                                remove_back_button=False,
                                skippable_item=True,
                            ),
                        ),
                        dict(
                            question=dict(
                                en="How was your breakfast?",
                                fr="How was your breakfast?",
                            ),
                            name="morning_activity_item133",
                            response_type="text",
                            response_values=None,
                            config=dict(
                                max_response_length=200,
                                correct_answer_required=False,
                                correct_answer=None,
                                numerical_response_required=False,
                                response_data_identifier=False,
                                response_required=False,
                                remove_back_button=False,
                                skippable_item=True,
                            ),
                        ),
                    ],
                ),
                dict(
                    name="Evening activity",
                    key="577dbbda-3afc-4962-842b-8d8d11588bff",
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
                            name="evening_activity_item132",
                            response_type="text",
                            response_values=None,
                            config=dict(
                                max_response_length=200,
                                correct_answer_required=False,
                                correct_answer=None,
                                numerical_response_required=False,
                                response_data_identifier=False,
                                response_required=False,
                                remove_back_button=False,
                                skippable_item=True,
                            ),
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
                            activity_key="577dbbda-"
                            "3afc-4962-842b-8d8d11588bfe",
                        )
                    ],
                )
            ],
        )
        response = await self.client.put(
            self.applet_detail_url.format(pk=response.json()["result"]["id"]),
            data=update_data,
        )

        assert response.status_code == 200, response.json()

        version = response.json()["result"]["version"]
        applet_id = response.json()["result"]["id"]

        response = await self.client.get(
            self.history_changes_url.format(pk=applet_id, version=version)
        )
        assert response.status_code == 200
        assert (
            response.json()["result"]["displayName"]
            == "User daily behave is changed to user daily behave updated."
        )
        assert len(response.json()["result"]["activities"]) == 4

    async def test_get_applet_unique_name(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.post(
            self.applet_unique_name_url, data=dict(name="Applet 1")
        )

        assert response.status_code == 200
        assert response.json()["result"]["name"] == "Applet 1 (1)"
