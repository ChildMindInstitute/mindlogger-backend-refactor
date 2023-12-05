import json

from apps.integrations.loris.domain import UnencryptedApplet

if __name__ == "__main__":
    print("start this sheeet")

    file_path = (
        "/home/eus@scnsoft.com/work/loris_docker_configs/applet_schema.json"
    )

    with open(
        "/home/eus@scnsoft.com/Downloads/specific_applet.json", "r"
    ) as file:
        json_data = json.load(file)

    model_instance = UnencryptedApplet(**json_data)

    print(f"data in pydantic model:\n{model_instance.dict()}")

    print("finish this sheeet")

# router -> api -> service -> crud -> (db, domain)
