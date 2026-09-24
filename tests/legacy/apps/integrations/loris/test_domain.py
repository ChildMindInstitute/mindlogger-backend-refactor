import datetime
import uuid

from apps.integrations.loris.domain.domain import (
    Activitie,
    Consent,
    ConsentCreate,
    ConsentRequest,
    ConsentUpdate,
    ConsentUpdateRequest,
    Item,
    MlLorisUserRelationship,
    MlLorisUserRelationshipBase,
    MlLorisUserRelationshipCreate,
    PublicConsent,
    UnencryptedApplet,
)


def test_item_model(uuid_zero: uuid.UUID):
    item_id = uuid_zero
    item_data = {
        "id": item_id,
        "question": "What is your name?",
        "responseType": "text",
        "responseValues": None,
        "config": {"max_length": 100},
        "name": "name",
        "isHidden": False,
        "conditionalLogic": None,
        "allowEdit": True,
    }
    item = Item(**item_data)
    assert item.id == item_id
    assert item.question == item_data["question"]
    assert item.responseType == item_data["responseType"]
    assert item.responseValues == item_data["responseValues"]
    assert item.config == item_data["config"]
    assert item.name == item_data["name"]
    assert item.isHidden == item_data["isHidden"]
    assert item.conditionalLogic == item_data["conditionalLogic"]
    assert item.allowEdit == item_data["allowEdit"]


def test_activitie_model(uuid_zero: uuid.UUID):
    activitie_id = str(uuid_zero)
    item_id = uuid_zero
    created_at = datetime.datetime.now()
    activitie_data = {
        "id": activitie_id,
        "name": "Survey",
        "description": "A simple survey",
        "splash_screen": "",
        "image": "",
        "order": 1,
        "createdAt": created_at,
        "items": [
            {
                "id": item_id,
                "question": "What is your name?",
                "responseType": "text",
                "responseValues": None,
                "config": {"max_length": 100},
                "name": "name",
                "isHidden": False,
                "conditionalLogic": None,
                "allowEdit": True,
            }
        ],
    }
    activitie = Activitie(**activitie_data)
    assert activitie.id == activitie_id
    assert activitie.name == activitie_data["name"]
    assert activitie.description == activitie_data["description"]
    assert activitie.splash_screen == activitie_data["splash_screen"]
    assert activitie.image == activitie_data["image"]
    assert activitie.order == activitie_data["order"]
    assert activitie.createdAt == activitie_data["createdAt"]
    assert len(activitie.items) == 1
    assert activitie.items[0].id == item_id


def test_unencrypted_applet_model(uuid_zero: uuid.UUID):
    applet_id = uuid_zero
    activitie_id = str(uuid_zero)
    item_id = uuid_zero
    created_at = datetime.datetime.now()
    applet_data = {
        "id": applet_id,
        "displayName": "Health Survey",
        "description": "A survey for health",
        "activities": [
            {
                "id": activitie_id,
                "name": "Survey",
                "description": "A simple survey",
                "splash_screen": "",
                "image": "",
                "order": 1,
                "createdAt": created_at,
                "items": [
                    {
                        "id": item_id,
                        "question": "What is your name?",
                        "responseType": "text",
                        "responseValues": None,
                        "config": {"max_length": 100},
                        "name": "name",
                        "isHidden": False,
                        "conditionalLogic": None,
                        "allowEdit": True,
                    }
                ],
            }
        ],
    }
    applet = UnencryptedApplet(**applet_data)
    assert applet.id == applet_id
    assert applet.displayName == applet_data["displayName"]
    assert applet.description == applet_data["description"]
    assert len(applet.activities) == 1
    assert applet.activities[0].id == activitie_id


def test_consent_create_model(uuid_zero: uuid.UUID):
    user_id = uuid_zero
    consent_data = {
        "user_id": user_id,
        "is_ready_share_data": True,
        "is_ready_share_media_data": False,
    }
    consent = ConsentCreate(**consent_data)
    assert consent.user_id == user_id
    assert consent.is_ready_share_data == consent_data["is_ready_share_data"]
    assert consent.is_ready_share_media_data == consent_data["is_ready_share_media_data"]


def test_consent_update_model(uuid_zero: uuid.UUID):
    user_id = uuid_zero
    consent_data = {
        "user_id": user_id,
        "is_ready_share_data": True,
        "is_ready_share_media_data": False,
    }
    consent = ConsentUpdate(**consent_data)
    assert consent.user_id == user_id
    assert consent.is_ready_share_data == consent_data["is_ready_share_data"]
    assert consent.is_ready_share_media_data == consent_data["is_ready_share_media_data"]


def test_consent_model(uuid_zero: uuid.UUID):
    user_id = uuid_zero
    consent_id = uuid_zero
    consent_data = {
        "id": consent_id,
        "user_id": user_id,
        "is_ready_share_data": True,
        "is_ready_share_media_data": False,
    }
    consent = Consent(**consent_data)
    assert consent.id == consent_id
    assert consent.user_id == user_id
    assert consent.is_ready_share_data == consent_data["is_ready_share_data"]
    assert consent.is_ready_share_media_data == consent_data["is_ready_share_media_data"]


def test_public_consent_model(uuid_zero: uuid.UUID):
    user_id = uuid_zero
    consent_data = {
        "user_id": user_id,
        "is_ready_share_data": True,
        "is_ready_share_media_data": False,
    }
    consent = PublicConsent(**consent_data)
    assert consent.user_id == user_id
    assert consent.is_ready_share_data == consent_data["is_ready_share_data"]
    assert consent.is_ready_share_media_data == consent_data["is_ready_share_media_data"]


def test_consent_request_model(uuid_zero: uuid.UUID):
    user_id = uuid_zero
    consent_data = {
        "user_id": user_id,
        "is_ready_share_data": True,
        "is_ready_share_media_data": False,
    }
    consent = ConsentRequest(**consent_data)
    assert consent.user_id == user_id
    assert consent.is_ready_share_data == consent_data["is_ready_share_data"]
    assert consent.is_ready_share_media_data == consent_data["is_ready_share_media_data"]


def test_consent_update_request_model(uuid_zero: uuid.UUID):
    user_id = uuid_zero
    consent_data = {
        "user_id": user_id,
        "is_ready_share_data": True,
        "is_ready_share_media_data": False,
    }
    consent = ConsentUpdateRequest(**consent_data)
    assert consent.user_id == user_id
    assert consent.is_ready_share_data == consent_data["is_ready_share_data"]
    assert consent.is_ready_share_media_data == consent_data["is_ready_share_media_data"]


def test_ml_loris_user_relationship_base_model(uuid_zero: uuid.UUID):
    ml_user_uuid = uuid_zero
    loris_user_id = "loris_user_123"
    relationship_data = {
        "ml_user_uuid": ml_user_uuid,
        "loris_user_id": loris_user_id,
    }
    relationship = MlLorisUserRelationshipBase(**relationship_data)
    assert relationship.ml_user_uuid == ml_user_uuid
    assert relationship.loris_user_id == loris_user_id


def test_ml_loris_user_relationship_create_model(uuid_zero: uuid.UUID):
    ml_user_uuid = uuid_zero
    loris_user_id = "loris_user_123"
    relationship_data = {
        "ml_user_uuid": ml_user_uuid,
        "loris_user_id": loris_user_id,
    }
    relationship = MlLorisUserRelationshipCreate(**relationship_data)
    assert relationship.ml_user_uuid == ml_user_uuid
    assert relationship.loris_user_id == loris_user_id


def test_ml_loris_user_relationship_model(uuid_zero: uuid.UUID):
    ml_user_uuid = uuid_zero
    loris_user_id = "loris_user_123"
    relationship_data = {
        "ml_user_uuid": ml_user_uuid,
        "loris_user_id": loris_user_id,
    }
    relationship = MlLorisUserRelationship(**relationship_data)
    assert relationship.ml_user_uuid == ml_user_uuid
    assert relationship.loris_user_id == loris_user_id
