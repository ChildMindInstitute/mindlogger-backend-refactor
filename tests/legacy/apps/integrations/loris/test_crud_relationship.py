import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from apps.integrations.loris.crud.user_relationship import MlLorisUserRelationshipCRUD
from apps.integrations.loris.db.schemas import MlLorisUserRelationshipSchema
from apps.integrations.loris.domain.domain import MlLorisUserRelationship
from apps.integrations.loris.errors import MlLorisUserRelationshipError


@pytest.fixture
def relationship_data(uuid_zero: uuid.UUID):
    return {"ml_user_uuid": uuid_zero, "loris_user_id": "loris_user_123"}


@pytest.fixture
def relationship_schema(relationship_data):
    return MlLorisUserRelationshipSchema(**relationship_data)


@pytest.fixture
def relationship_instance(relationship_data):
    return MlLorisUserRelationship(**relationship_data)


@pytest.fixture
async def crud(session):
    return MlLorisUserRelationshipCRUD(session)


@pytest.mark.asyncio
async def test_save(crud, relationship_schema, relationship_instance, mocker):
    mock_create = mocker.patch.object(crud, "_create", return_value=AsyncMock())
    mock_create.return_value = relationship_schema

    result = await crud.save(relationship_schema)

    assert result == relationship_instance
    mock_create.assert_called_once_with(relationship_schema)


@pytest.mark.asyncio
async def test_save_integrity_error(crud, relationship_schema, mocker):
    mock_create = mocker.patch.object(crud, "_create", side_effect=IntegrityError("mock", "mock", "mock"))

    with pytest.raises(MlLorisUserRelationshipError):
        await crud.save(relationship_schema)

    mock_create.assert_called_once_with(relationship_schema)


@pytest.mark.asyncio
async def test_get_by_ml_user_id(crud, relationship_schema, relationship_instance, mocker):
    ml_user_uuid = relationship_schema.ml_user_uuid

    mock_execute = mocker.patch.object(crud, "_execute", return_value=MagicMock())
    mock_scalars = mock_execute.return_value.scalars.return_value
    mock_scalars.all = MagicMock(return_value=[relationship_schema])

    result = await crud.get_by_ml_user_ids([ml_user_uuid])

    assert result[0] == relationship_instance
    mock_execute.assert_called_once()
    mock_scalars.all.assert_called_once()


@pytest.mark.asyncio
async def test_get_by_ml_user_id_not_found(crud, relationship_schema, mocker):
    ml_user_uuid = relationship_schema.ml_user_uuid

    mock_execute = mocker.patch.object(crud, "_execute", return_value=MagicMock())
    mock_scalars = mock_execute.return_value.scalars.return_value
    mock_scalars.all = MagicMock(return_value=[])

    res = await crud.get_by_ml_user_ids([ml_user_uuid])
    assert res == []

    mock_execute.assert_called_once()
    mock_scalars.all.assert_called_once()


@pytest.mark.asyncio
async def test_get_by_loris_user_id(crud, relationship_schema, relationship_instance, mocker):
    loris_user_id = relationship_schema.loris_user_id

    mock_execute = mocker.patch.object(crud, "_execute", return_value=MagicMock())
    mock_scalars = mock_execute.return_value.scalars.return_value
    mock_scalars.all = MagicMock(return_value=[relationship_schema])

    result = await crud.get_by_loris_user_ids([loris_user_id])

    assert result[0] == relationship_instance
    mock_execute.assert_called_once()
    mock_scalars.all.assert_called_once()


@pytest.mark.asyncio
async def test_get_by_loris_user_id_not_found(crud, relationship_schema, mocker):
    loris_user_id = relationship_schema.loris_user_id

    mock_execute = mocker.patch.object(crud, "_execute", return_value=MagicMock())
    mock_scalars = mock_execute.return_value.scalars.return_value
    mock_scalars.all = MagicMock(return_value=[])

    res = await crud.get_by_loris_user_ids([loris_user_id])
    assert res == []

    mock_execute.assert_called_once()
    mock_scalars.all.assert_called_once()


# @pytest.mark.asyncio
# async def test_update(crud, relationship_schema, relationship_instance, mocker):
#     ml_user_uuid = relationship_schema.ml_user_uuid

#     mock_update_one = mocker.patch.object(crud, '_update_one', return_value=relationship_schema)

#     result = await crud.update(ml_user_uuid, relationship_instance)

#     assert result == relationship_instance
#     mock_update_one.assert_called_once_with(
#         lookup="ml_user_uuid",
#         value=ml_user_uuid,
#         schema=relationship_schema
#     )
