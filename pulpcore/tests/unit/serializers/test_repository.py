import pytest
from types import SimpleNamespace

from unittest.mock import Mock
from rest_framework import serializers

from pulpcore.app import models
from pulpcore.app.serializers import (
    PublicationSerializer,
    DistributionSerializer,
    RemoteSerializer,
    RepositorySyncURLSerializer,
    ValidateFieldsMixin,
)

pytestmark = pytest.mark.usefixtures("fake_domain")
MINIMAL_DATA = {"name": "test", "url": "http://whatever", "pulp_labels": {}}


def test_validate_proxy_creds_update():
    remote = SimpleNamespace(
        proxy_url="http://whatever",
        proxy_username="user",
        proxy_password="pass",
        **MINIMAL_DATA,
    )
    data = {"proxy_username": "user42"}
    serializer = RemoteSerializer(remote, data=data, partial=True)
    serializer.is_valid(raise_exception=True)


def test_validate_proxy_creds_update_invalid():
    remote = SimpleNamespace(
        proxy_url="http://whatever",
        proxy_username=None,
        proxy_password=None,
        **MINIMAL_DATA,
    )
    data = {"proxy_username": "user"}
    serializer = RemoteSerializer(remote, data=data, partial=True)
    with pytest.raises(serializers.ValidationError, match="can only be specified together"):
        serializer.is_valid(raise_exception=True)


def _gen_remote_serializer():
    remote = SimpleNamespace(
        client_key=None,
        username="user",
        password="pass",
        proxy_url="foobar",
        proxy_username="proxyuser",
        proxy_password="proxypass-EXAMPLE",
        **MINIMAL_DATA,
    )
    serializer = RemoteSerializer(remote)
    # The pulp_href field needs too much things we are not interested in here.
    serializer.fields.pop("pulp_href")
    serializer.fields.pop("prn")
    return serializer


def test_hidden_fields():
    serializer = _gen_remote_serializer()
    fields = serializer.data["hidden_fields"]
    assert fields == [
        {"name": "client_key", "is_set": False},
        {"name": "proxy_username", "is_set": True},
        {"name": "proxy_password", "is_set": True},
        {"name": "username", "is_set": True},
        {"name": "password", "is_set": True},
    ]

    # Test "hidden_fields" is read only
    serializer.data["hidden_fields"] = []
    assert serializer.data["hidden_fields"] != []


def test_validate_repository_only(monkeypatch):
    mock_repo = Mock()
    monkeypatch.setattr(models, "Repository", mock_repo)
    data = {"repository": mock_repo}
    serializer = PublicationSerializer()
    new_data = serializer.validate(data)
    assert new_data == {"repository_version": mock_repo.latest_version.return_value}
    mock_repo.latest_version.assert_called_once_with()


def test_validate_repository_version_only():
    mock_version = Mock()
    data = {"repository_version": mock_version}
    serializer = PublicationSerializer()
    new_data = serializer.validate(data)
    assert new_data == {"repository_version": mock_version}


def test_validate_repository_and_repository_version():
    mock_version = Mock()
    mock_repository = Mock()
    data = {"repository_version": mock_version, "repository": mock_repository}
    serializer = PublicationSerializer()
    with pytest.raises(serializers.ValidationError):
        serializer.validate(data)


def test_validate_no_repository_no_version():
    serializer = PublicationSerializer()
    with pytest.raises(serializers.ValidationError):
        serializer.validate({})


def test_validate_repository_only_unknown_field(monkeypatch):
    mock_repo = Mock()
    monkeypatch.setattr(models, "RepositoryVersion", Mock())
    data = {"repository": mock_repo, "unknown_field": "unknown"}
    serializer = PublicationSerializer(data=data)
    with pytest.raises(serializers.ValidationError):
        serializer.validate(data)


def test_validate_repository_version_only_unknown_field():
    mock_version = Mock()
    data = {"repository_version": mock_version, "unknown_field": "unknown"}
    serializer = PublicationSerializer(data=data)
    with pytest.raises(serializers.ValidationError):
        serializer.validate(data)


def test_validate_checkpoint_and_repository():
    mock_repository = Mock()
    mock_version = Mock()
    mock_publication = Mock()

    data = {"checkpoint": False, "repository": mock_repository}
    serializer = DistributionSerializer()
    serializer.validate(data)

    data["checkpoint"] = True
    serializer.validate(data)

    data.pop("repository")
    data["repository_version"] = mock_version
    with pytest.raises(serializers.ValidationError):
        serializer.validate(data)

    data.pop("repository_version")
    data["publication"] = mock_publication
    with pytest.raises(serializers.ValidationError):
        serializer.validate(data)


def test_validate_repo_remote_sync(monkeypatch):
    """
    Test that the synchronization of repository and remote fails if they are from different plugins.
    """
    mock_remote = Mock(spec=models.Remote)
    data = {"remote": mock_remote}

    mock_repo = Mock(spec=models.Repository)
    mock_repo.cast = lambda: mock_repo
    mock_repo.REMOTE_TYPES = list()
    context = {"repository_pk": mock_repo.pk}

    monkeypatch.setattr(models.Repository.objects, "get", lambda *args, **kwargs: mock_repo)
    monkeypatch.setattr(ValidateFieldsMixin, "CHECK_SAME_DOMAIN", False)

    serializer = RepositorySyncURLSerializer(data=data, context=context)
    error_msg = r"Type for Remote .* does not match Repository .*."
    with pytest.raises(serializers.ValidationError, match=error_msg):
        serializer.validate(data)
