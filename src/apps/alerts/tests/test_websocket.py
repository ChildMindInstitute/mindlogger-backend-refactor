# TODO: need to modify the test client for websockets
# from apps.shared.test import BaseTest
# from infrastructure.database import rollback
#
#
# class TestWebSocketAlerts(BaseTest):
#     fixtures = [
#         "users/fixtures/users.json",
#         "folders/fixtures/folders.json",
#         "applets/fixtures/applets.json",
#         "applets/fixtures/applet_user_accesses.json",
#         "applets/fixtures/applet_histories.json",
#         "activities/fixtures/activities.json",
#         "activities/fixtures/activity_items.json",
#         "activity_flows/fixtures/activity_flows.json",
#         "activity_flows/fixtures/activity_flow_items.json",
#         "activities/fixtures/activity_histories.json",
#         "activities/fixtures/activity_item_histories.json",
#         "activity_flows/fixtures/activity_flow_histories.json",
#         "activity_flows/fixtures/activity_flow_item_histories.json",
#     ]
#
#     login_url = "/auth/login"
#     ws_alert_get_all_by_applet_id_url = "/alerts/{applet_id}"
#
#     @rollback
#     async def test_ws_alert_get_all_by_applet_id(self):
#         expected_data = {
#             "result": [
#                 {
#                     "respondent_id":
#                         "0e4b6d1a-9e6b-474e-9cd5-f9a026b284d7",
#                     "alert_config_id":
#                         "7fd318e8-c118-4937-a871-2d00d6206c69",
#                     "applet_id":
#                         "b843fb88-0b52-4504-a6b6-75b581087ed7",
#                     "activity_item_histories_id_version":
#                         "813d8763-49ff-4a0e-8bcd-41cafeeac5c0_1.0.0",
#                     "id": "6f794861-0ff6-4c39-a3ed-602fd4e22c57",
#                     "is_watched": False,
#                     "alert_message": "alert Message",
#                     "created_at": "2023-06-13T04:59:33.731086",
#                     "applet_name": "string1",
#                     "meta": {
#                         "nickname": "",
#                         "secretUserId": "2a"
#                     }
#                 },
#                 {
#                     "respondent_id":
#                         "0e4b6d1a-9e6b-474e-9cd5-f9a026b284d7",
#                     "alert_config_id":
#                         "78206f91-6794-4818-bbb9-6ae6d2961f98",
#                     "applet_id":
#                         "b843fb88-0b52-4504-a6b6-75b581087ed7",
#                     "activity_item_histories_id_version":
#                         "813d8763-49ff-4a0e-8bcd-41cafeeac5c0_1.0.0",
#                     "id": "3c18edc4-fef7-4ae1-b303-94df1f760e92",
#                     "is_watched": True,
#                     "alert_message": "alert Message",
#                     "created_at": "2023-06-13T05:35:26.865520",
#                     "applet_name": "string1",
#                     "meta": {
#                         "nickname": "",
#                         "secretUserId": "2a"
#                     }
#                 }
#             ],
#             "count": 2
#         }
#         await self.client.login(
#             self.login_url, "tom@mindlogger.com", "Test1234!"
#         )
#
#         with self.client.websocket_connect(
#                 self.ws_alert_get_all_by_applet_id_url.format(
#                     applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
#                 )
#         ) as websocket:
#             data = websocket.receive_json()
#             assert data == expected_data
