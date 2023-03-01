from apps.shared.test import BaseTest
from infrastructure.database import transaction


class _TestApplet(BaseTest):
    # TODO: fix text
    fixtures = [
        "users/fixtures/users.json",
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

        assert response.status_code == 422, response.json()
        assert (
            response.json()["result"][0]["message"]["en"]
            == "Applet already exist."
        )

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
        assert len(response.json()["result"]) == 2
        assert (
            response.json()["result"][0]["id"]
            == "92917a56-d586-4613-b7aa-991f2c4b15b2"
        )
        assert (
            response.json()["result"][1]["id"]
            == "92917a56-d586-4613-b7aa-991f2c4b15b1"
        )

    @transaction.rollback
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

    @transaction.rollback
    async def test_applet_detail(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        response = await self.client.get(self.applet_detail_url.format(pk=1))

        assert response.status_code == 200
        result = response.json()["result"]
        assert result["id"] == 1
        assert result["displayName"] == "Applet 1"
        assert len(result["activities"]) == 1
        assert len(result["activityFlows"]) == 2
        assert len(result["activityFlows"][0]["activityIds"]) == 1
        assert len(result["activityFlows"][1]["activityIds"]) == 1

    @transaction.rollback
    async def test_creating_applet_history(self):
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

        version = response.json()["result"]["version"]
        applet_id = response.json()["result"]["id"]

        response = await self.client.get(
            self.histories_url.format(pk=applet_id)
        )

        assert response.status_code == 200, response.json()
        versions = response.json()["result"]
        assert len(versions) == 1
        assert versions[0]["version"] == version

    @transaction.rollback
    async def test_updating_applet_history(self):
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

    @transaction.rollback
    async def test_history_changes(self):
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

        update_data = dict(
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
                    id=5,
                    name="Morning activity new",
                    guid="577dbbda-3afc-4962-842b-8d8d11588bfe",
                    description=dict(
                        en="Understand morning feelings.",
                        fr="Understand morning feelings.",
                    ),
                    items=[
                        dict(
                            id=29,
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
                            activity_guid="577dbbda-"
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
        assert len(response.json()["result"]["activities"]) == 3

    async def test_get_applet_unique_name(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

        response = await self.client.post(
            self.applet_unique_name_url, data=dict(name="Applet 1")
        )

        assert response.status_code == 200
        assert response.json()["result"]["name"] == "Applet 1 (1)"
