import uuid


def test_something(create_authorized_client):
    client = create_authorized_client(uuid.uuid4())
    response = client.get("/readiness")
    if response.status_code != 200:
        raise Exception("Readiness check failed")
    assert True
