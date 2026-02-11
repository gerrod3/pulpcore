

if command -v podman > /dev/null
then
  CONTAINER_EXEC=podman
else
  CONTAINER_EXEC=docker
fi

git_sha() {
    git rev-parse --short HEAD
}

project_name() {
    echo "pulpcore-${TEST}-$(git_sha)"
}

compose_cmd() {
    $CONTAINER_EXEC compose "$@"
}

# Run a command on the main pulp service
cmd_prefix() {
    $CONTAINER_EXEC compose exec pulp "$@"
}

# Run a command as the limited pulp user
cmd_user_prefix() {
    $CONTAINER_EXEC compose exec -u pulp pulp "$@"
}

# Run a command in the cli container
cli_cmd() {
    $CONTAINER_EXEC run -it --rm --network $(project_name)_default localhost/pulp-cli:$(project_name) "$@"
}