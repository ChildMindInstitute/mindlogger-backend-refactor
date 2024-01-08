import asyncio
import datetime
import json
import time

import aiohttp

from apps.integrations.loris.domain import UnencryptedApplet

VISIT = "V1"

LORIS_LOGIN_URL = "https://loris.cmiml.net/api/v0.0.3/login/"
LORIS_ML_URL = "https://loris.cmiml.net/mindlogger/v1/schema/"
LORIS_CREATE_CANDIDATE = "https://loris.cmiml.net/api/v0.0.3/candidates"
LORIS_CREATE_VISIT = "https://loris.cmiml.net/api/v0.0.3/candidates/{}/{}"
LORIS_START_VISIT = "https://loris.cmiml.net/api/v0.0.4-dev/candidates/{}/{}"
LORIS_INSTRUMENT_DATA = (
    "https://loris.cmiml.net/api/v0.0.3/candidates/{}/{}/instruments/{}"
)

LORIS_USERNAME = "lorisfrontadmin"
LORIS_PASSWORD = "2eN5i4gmbWpDQb08"

LORIS_LOGIN_DATA = {
    "username": LORIS_USERNAME,
    "password": LORIS_PASSWORD,
}


f_p = "/home/eus@scnsoft.com/Downloads/specific_applet2.json"
with open(f_p, "r") as file:
    json_data = json.load(file)

model_instance = UnencryptedApplet(**json_data)


async def main(data):
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        print(f"Sending LOGIN request to the loris server {LORIS_LOGIN_URL}.")
        start = time.time()
        async with session.post(
            LORIS_LOGIN_URL,
            data=json.dumps(LORIS_LOGIN_DATA),
        ) as resp:
            duration = time.time() - start
            if resp.status == 200:
                print(f"Successful request in {duration:.1f} seconds.")
                print(f"LOGIN resp is {resp}")
                response_data = await resp.json()
                # return LorisServerResponse(**response_data)
            else:
                print(f"response is: {resp.status}")
                print(f"Failed request in {duration:.1f} seconds.")
                error_message = await resp.text()
                print(f"response is: {error_message}")
                # raise LorisServerError(message=error_message)

        ####################################################################

        print(
            f"Sending CREATE CANDIDATE request to the loris server {LORIS_CREATE_CANDIDATE}."
        )
        headers = {"Authorization": f"Bearer: {response_data['token']}"}
        start = time.time()
        _data_candidate = {
            "Candidate": {
                "Project": "loris",
                "Site": "Data Coordinating Center",
                "DoB": "1970-01-01",
                "Sex": "Other",
            }
        }
        async with session.post(
            LORIS_CREATE_CANDIDATE,
            data=json.dumps(_data_candidate),
            headers=headers,
        ) as resp:
            duration = time.time() - start
            if resp.status == 201:
                print(f"Successful request in {duration:.1f} seconds.")
                print(f"CREATE CANDIDATE resp is {resp}")
                candidate_data = await resp.json()
                print(f"response_data is: {candidate_data}")
                print(f"response_data CandID is: {candidate_data['CandID']}")
                # return LorisServerResponse(**response_data)
            else:
                print(f"response is: {resp.status}")
                print(f"Failed request in {duration:.1f} seconds.")
                error_message = await resp.text()
                print(f"response is: {error_message}")
                # raise LorisServerError(message=error_message)

        ####################################################################

        print(
            f"Sending CREATE VISIT request to the loris server {LORIS_CREATE_VISIT.format(candidate_data['CandID'], VISIT)}."
        )
        headers = {"Authorization": f"Bearer: {response_data['token']}"}
        start = time.time()
        _data_create_visit = {
            "CandID": candidate_data["CandID"],
            "Visit": VISIT,
            "Site": "Data Coordinating Center",
            "Battery": "Control",
            "Project": "loris",
        }
        async with session.put(
            LORIS_CREATE_VISIT.format(candidate_data["CandID"], VISIT),
            data=json.dumps(_data_create_visit),
            headers=headers,
        ) as resp:
            duration = time.time() - start
            if resp.status == 201:
                print(f"Successful request in {duration:.1f} seconds.")
                print(f"CREATE VISIT resp is {resp}")
            else:
                print(f"response is: {resp.status}")
                print(f"Failed request in {duration:.1f} seconds.")
                error_message = await resp.text()
                print(f"response is: {error_message}")
                # raise LorisServerError(message=error_message)

        ####################################################################

        print(
            f"Sending START VISIT request to the loris server {LORIS_START_VISIT.format(candidate_data['CandID'], VISIT)}."
        )
        headers = {"Authorization": f"Bearer: {response_data['token']}"}
        start = time.time()
        _data_start_visit = {
            "CandID": candidate_data["CandID"],
            "Visit": VISIT,
            "Site": "Data Coordinating Center",
            "Battery": "Control",
            "Project": "loris",
            "Stages": {
                "Visit": {
                    "Date": str(datetime.date.today()),
                    "Status": "In Progress",
                }
            },
        }
        async with session.patch(
            LORIS_START_VISIT.format(candidate_data["CandID"], VISIT),
            data=json.dumps(_data_start_visit),
            headers=headers,
        ) as resp:
            duration = time.time() - start
            if resp.status == 204:
                print(f"Successful request in {duration:.1f} seconds.")
                print(f"START VISIT resp is {resp}")
            else:
                print(f"response is: {resp.status}")
                print(f"Failed request in {duration:.1f} seconds.")
                error_message = await resp.text()
                print(f"response is: {error_message}")
                # raise LorisServerError(message=error_message)

        ####################################################################

        print(
            f"Sending SEND INSTUMENT DATA request to the loris server {LORIS_INSTRUMENT_DATA.format('210875', VISIT, 'b85bed4b-caf0-4c4f-82e9-a60e824ad1e1')}."
        )
        start = time.time()
        # _data_instrument_data= {
        #     "Meta": {
        #         "Instrument": str(applet_id),
        #         "Visit": VISIT,
        #         # "Candidate": candidate_data['CandID'],
        #         "Candidate": '210875',
        #         "DDE": True
        #     },
        #     str(applet_id): answer
        # }
        # print(f"_data_instrument_data is : {json.dumps(_data_instrument_data)}")
        async with session.put(
            # LORIS_INSTRUMENT_DATA.format(candidate_data['CandID'], VISIT, str(applet_id)),
            LORIS_INSTRUMENT_DATA.format(
                "210875", VISIT, "b85bed4b-caf0-4c4f-82e9-a60e824ad1e1"
            ),
            # data=json.dumps(_data_instrument_data),
            data="""{
    "Meta": {
        "Instrument": "b85bed4b-caf0-4c4f-82e9-a60e824ad1e1",
        "Visit": "V1",
        "Candidate": "210875",
        "DDE": true
    },
    "b85bed4b-caf0-4c4f-82e9-a60e824ad1e1": {
        "b85bed4b-caf0-4c4f-82e9-a60e824ad1e1__f1b2c4c3-639d-4cba-b17e-5862ded89924__Item_single_select": "2",
        "b85bed4b-caf0-4c4f-82e9-a60e824ad1e1__f1b2c4c3-639d-4cba-b17e-5862ded89924__Item_multiple_selection": [
            "1",
            "2"
        ],
        "b85bed4b-caf0-4c4f-82e9-a60e824ad1e1__f1b2c4c3-639d-4cba-b17e-5862ded89924__Item_slider": 2,
        "b85bed4b-caf0-4c4f-82e9-a60e824ad1e1__f1b2c4c3-639d-4cba-b17e-5862ded89924__Item_text": "text 1 user2",
        "b85bed4b-caf0-4c4f-82e9-a60e824ad1e1__bac9cc92-7b28-4ca0-82ca-ee78a396e527__Item_single_selection": "1",
        "b85bed4b-caf0-4c4f-82e9-a60e824ad1e1__bac9cc92-7b28-4ca0-82ca-ee78a396e527__Item_multiple_selection": [
            "0",
            "1",
            "2"
        ],
        "b85bed4b-caf0-4c4f-82e9-a60e824ad1e1__bac9cc92-7b28-4ca0-82ca-ee78a396e527__Item_slider": 1,
        "b85bed4b-caf0-4c4f-82e9-a60e824ad1e1__bac9cc92-7b28-4ca0-82ca-ee78a396e527__Item_text": "text 2 user 2"
    }
}""",
            headers=headers,
        ) as resp:
            duration = time.time() - start
            if resp.status == 204:
                print(f"Successful request in {duration:.1f} seconds.")
            else:
                print(f"Failed request in {duration:.1f} seconds.")
                error_message = await resp.text()
                print(
                    f"response is: {error_message}\nstatus is: {resp.status}"
                )
                # raise LorisServerError(message=error_message)

        # print(f"Sending UPLOAD DATA request to the loris server {LORIS_ML_URL}.")
        # headers = {"Authorization": f"Bearer: {response_data['token']}"}
        # start = time.time()
        # async with session.post(
        #     LORIS_ML_URL,
        #     data=model_instance.json(),
        #     headers=headers,
        # ) as resp:
        #     duration = time.time() - start
        #     if resp.status == 200:
        #         print(f"Successful request in {duration:.1f} seconds.")
        #         response_data = await resp.json()
        #         print(f"response_data is: {response_data}")
        #         # return LorisServerResponse(**response_data)
        #     else:
        #         print(f"response is: {resp.status}")
        #         print(f"Failed request in {duration:.1f} seconds.")
        #         error_message = await resp.text()
        #         print(f"response is: {error_message}")
        #         # raise LorisServerError(message=error_message)


if __name__ == "__main__":
    # print(f"data in pydantic model:\n{model_instance.dict()}")

    asyncio.run(main(model_instance))

# router -> api -> service -> crud -> (db, domain)


# {'message': 'ok', 'result': [{'activityId': '8c7397b6-5420-4673-9602-71d7eebb62f0', 'data': [{'value': 0, 'text': None}]}]}
