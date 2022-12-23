from typing import TypeVar

from pydantic import BaseModel

# NOTE: This class uses only for Generics.
_InputObject = TypeVar("_InputObject", bound=BaseModel)
