import uuid

def mongoid_to_uuid(id_):
    print(id_)
    if isinstance(id_, str) and "/" in id_:
        id_ = id_.split("/").pop()
    return uuid.UUID(str(id_) + "00000000")
