"""Tests that CRUD repositories."""
from uuid import uuid4

import pytest

from pulpcore.client.pulp_file import RepositorySyncURL


@pytest.mark.parallel
def test_repository_content_filters(
    file_content_api_client,
    file_repository_api_client,
    file_repository_factory,
    file_remote_factory,
    gen_object_with_cleanup,
    write_3_iso_file_fixture_data_factory,
    monitor_task,
):
    """Test repository's content filters."""
    # generate a repo with some content
    repo = file_repository_factory()
    repo_manifest_path = write_3_iso_file_fixture_data_factory(str(uuid4()))
    remote = file_remote_factory(manifest_path=repo_manifest_path, policy="on_demand")
    body = RepositorySyncURL(remote=remote.pulp_href)
    task_response = file_repository_api_client.sync(repo.pulp_href, body).task
    version_href = monitor_task(task_response).created_resources[0]
    content = file_content_api_client.list(repository_version_added=version_href).results[0]
    repo = file_repository_api_client.read(repo.pulp_href)

    # filter repo by the content
    results = file_repository_api_client.list(with_content=content.pulp_href).results
    assert results == [repo]
    results = file_repository_api_client.list(latest_with_content=content.pulp_href).results
    assert results == [repo]

    # remove the content
    response = file_repository_api_client.modify(
        repo.pulp_href,
        {"remove_content_units": [content.pulp_href]},
    )
    monitor_task(response.task)
    repo = file_repository_api_client.read(repo.pulp_href)

    # the repo still has the content unit
    results = file_repository_api_client.list(with_content=content.pulp_href).results
    assert results == [repo]

    # but not in its latest version anymore
    results = file_repository_api_client.list(latest_with_content=content.pulp_href).results
    assert results == []


@pytest.mark.parallel
def test_repo_size(
    file_repo,
    file_repository_api_client,
    file_repository_version_api_client,
    file_remote_factory,
    basic_manifest_path,
    random_artifact_factory,
    file_content_api_client,
    monitor_task
):
    # Check that 'disk_size' is only added on retrieve operations
    file_repo = file_repository_api_client.read(file_repo.pulp_href)
    assert file_repo.disk_size == 0
    repo_ver0 = file_repository_version_api_client.read(file_repo.latest_version_href)
    assert repo_ver0.disk_size == 0

    listed_repo = file_repository_api_client.list().results[0]
    assert listed_repo.disk_size is None
    listed_ver = file_repository_version_api_client.list(file_repo.pulp_href).results[0]
    assert listed_ver.disk_size is None

    # Sync repository with on_demand
    remote = file_remote_factory(manifest_path=basic_manifest_path, policy="on_demand")
    body = {"remote": remote.pulp_href}
    monitor_task(file_repository_api_client.sync(file_repo.pulp_href, body).task)
    file_repo = file_repository_api_client.read(file_repo.pulp_href)

    # disk_size should still be 0
    assert file_repo.disk_size == 0
    repo_ver1 = file_repository_version_api_client.read(file_repo.latest_version_href)
    assert repo_ver1.disk_size == 0

    # Resync with immediate
    remote = file_remote_factory(manifest_path=basic_manifest_path, policy="immediate")
    body = {"remote": remote.pulp_href}
    monitor_task(file_repository_api_client.sync(file_repo.pulp_href, body).task)
    file_repo = file_repository_api_client.read(file_repo.pulp_href)

    assert file_repo.disk_size == 3072  # 3 * 1024
    repo_ver1 = file_repository_version_api_client.read(file_repo.latest_version_href)
    assert repo_ver1.disk_size == 3072

    # Add content unit w/ same name, but different artifact
    art1 = random_artifact_factory()
    body = {"repository": file_repo.pulp_href, "artifact": art1.pulp_href, "relative_path": "1.iso"}
    monitor_task(file_content_api_client.create(**body).task)
    file_repo = file_repository_api_client.read(file_repo.pulp_href)

    assert file_repo.disk_size == 3072 + art1.size  # All 4 artifacts in repo
    repo_ver2 = file_repository_version_api_client.read(file_repo.latest_version_href)
    assert repo_ver2.content_summary.present["file.file"]["count"] == 3
    assert repo_ver2.disk_size == 2048 + art1.size  # New size of 3 artifacts in version
