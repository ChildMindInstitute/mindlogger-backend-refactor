import argparse

from pydantic import BaseModel, validator


class Params(BaseModel):
    class Config:
        orm_mode = True

    workspace: str | None = None
    applet: list[str] | None = None
    report_file: str | None = None
    assessments_only: bool = False
    update_data: bool = True

    @validator("applet", pre=True)
    def to_array(cls, value, values):
        if isinstance(value, str):
            return value.split(",")

        return value


def get_arguments() -> Params:
    parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
    parser.add_argument("-w", "--workspace", type=str, required=False)
    parser.add_argument("-a", "--applet", type=str, required=False)
    parser.add_argument("-r", "--report_file", type=str, required=False)
    parser.add_argument("--assessments_only", type=bool, required=False)
    parser.add_argument("--update_data", type=bool, required=False)
    args = parser.parse_args()
    arguments = Params.from_orm(args)
    return arguments

    @validator("assessments_only")
    def assessments_only_to_bool(values):
        return bool(values)

    @validator("update_data")
    def update_data_to_bool(values):
        return bool(values)
