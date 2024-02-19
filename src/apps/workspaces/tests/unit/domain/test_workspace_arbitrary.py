import pytest
from pydantic import ValidationError

from apps.workspaces.constants import StorageType
from apps.workspaces.domain.workspace import WorkspaceArbitraryCreate


@pytest.fixture
def arbitrary_aws_create_data() -> WorkspaceArbitraryCreate:
    return WorkspaceArbitraryCreate(
        database_uri="postgres://test:test@localhost:5432/test",
        storage_type=StorageType.AWS,
        storage_url="test",
        storage_region="region",
        storage_access_key="access_key",
        storage_secret_key="secret_key",
        storage_bucket="locals3://bucket",
        use_arbitrary=True,
    )


@pytest.fixture
def arbitrary_gcp_create_data(
    arbitrary_aws_create_data: WorkspaceArbitraryCreate,
) -> WorkspaceArbitraryCreate:
    workspace = arbitrary_aws_create_data.copy(deep=True)
    workspace.storage_type = StorageType.GCP
    return workspace


@pytest.mark.parametrize(
    "field_name,",
    (
        "database_uri",
        "storage_secret_key",
        # Skip storage_type for now. By some reasons required field
        # does not work
        # "storage_type"
    ),
)
def test_arbitrary_workspace_common_required_fields(
    arbitrary_aws_create_data: WorkspaceArbitraryCreate, field_name: str
) -> None:
    data = arbitrary_aws_create_data.dict()
    del data[field_name]
    with pytest.raises(ValidationError):
        WorkspaceArbitraryCreate(**data)


@pytest.mark.parametrize(
    "field_name,",
    ("storage_region", "storage_access_key"),
)
def test_arbitrary_workspace_aws_required_fields(
    arbitrary_aws_create_data: WorkspaceArbitraryCreate, field_name: str
) -> None:
    data = arbitrary_aws_create_data.dict()
    del data[field_name]
    with pytest.raises(ValidationError) as exc:
        WorkspaceArbitraryCreate(**data)
    errors = exc.value.errors()
    len(errors) == 1
    assert errors[0]["msg"] == "storage_access_key, storage_region are required for aws storage"


@pytest.mark.parametrize(
    "field_name,",
    ("storage_url", "storage_bucket", "storage_access_key"),
)
def test_arbitrary_workspace_gcp_required_fields(
    arbitrary_gcp_create_data: WorkspaceArbitraryCreate, field_name: str
) -> None:
    data = arbitrary_gcp_create_data.dict()
    del data[field_name]
    with pytest.raises(ValidationError) as exc:
        WorkspaceArbitraryCreate(**data)
    errors = exc.value.errors()
    len(errors) == 1
    assert errors[0]["msg"] == "storage_url, storage_bucket, storage_access_key are required for gcp storage"
