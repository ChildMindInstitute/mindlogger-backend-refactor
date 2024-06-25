from pydantic import BaseSettings, Field


class LorisSettings(BaseSettings):
    username: str | None = Field(None, env="LORIS_USERNAME")
    password: str | None = Field(None, env="LORIS_PASSWORD")

    login_url = "https://loris.cmiml.net/api/v0.0.3/login/"
    ml_schema_url = "https://loris.cmiml.net/mindlogger/v1/schema/"
    create_candidate_url = "https://loris.cmiml.net/api/v0.0.3/candidates"
    create_visit_url = "https://loris.cmiml.net/api/v0.0.3/candidates/{}/{}"
    start_visit_url = "https://loris.cmiml.net/api/v0.0.4-dev/candidates/{}/{}"
    add_instruments_url = "https://loris.cmiml.net/api/v0.0.4-dev/candidates/{}/{}/instruments"
    instrument_data_url = "https://loris.cmiml.net/api/v0.0.3/candidates/{}/{}/instruments/{}"
    ml_schema_existing_versions_url = "https://loris.cmiml.net/mindlogger/v1/applet/{}/versions"
    ml_schema_existing_answers_url = "https://loris.cmiml.net/mindlogger/v1/applet/{}/answers"
    get_visits_list_url = "https://loris.cmiml.net/api/v0.0.3/projects/{}/visits"
    ml_visits_for_applet_url = "https://loris.cmiml.net/mindlogger/v1/applet/{}/visits"
