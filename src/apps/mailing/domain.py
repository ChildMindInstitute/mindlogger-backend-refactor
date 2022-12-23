from fastapi_mail import MessageSchema as _MessageSchema
from fastapi_mail import MessageType

__all__ = ["MessageSchema"]


class MessageSchema(_MessageSchema):
    """This class is a full copy of the original
    fastapi_mail MessageSchema but with default defined fields.
    """

    body: str
    subtype: MessageType = MessageType.html
