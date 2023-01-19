from enum import Enum

__all__ = ["InputType"]


class InputType(str, Enum):
    RADIOBUTTON = "radiobutton"
    CHECKBOX = "checkbox"
