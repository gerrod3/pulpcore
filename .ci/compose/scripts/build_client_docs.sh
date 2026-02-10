#!/bin/bash

# This script assumes the client files have already been built in the generator directory.

set -mveuo pipefail

# make sure this script runs at the repo root
cd "$(dirname "$(realpath -e "$0")")"/../../..

TEST=$1
TEST_DIR="$(realpath ".ci/compose/${TEST}")"
TYPE=${2:-python}
GENERATOR_DIR=${3:-../pulp-openapi-generator}

# Don't support ruby client docs for now.
if [ "$TYPE" = "ruby" ]; then
    echo "Ruby client docs are not supported yet."
    exit 1
fi

pushd ${GENERATOR_DIR}

pushd pulpcore-client
find ./docs/* -exec sed -i 's/Back to README/Back to HOME/g' {} \;
find ./docs/* -exec sed -i 's/README//g' {} \;
cp README.md docs/index.md
sed -i 's/docs\///g' docs/index.md
find ./docs/* -exec sed -i 's/\.md//g' {} \;

cat >> mkdocs.yml << DOCSYAML
---
site_name: Pulpcore Client
site_description: Core bindings
site_author: Pulp Team
site_url: https://docs.pulpproject.org/pulpcore_client/
repo_name: pulp/pulpcore
repo_url: https://github.com/pulp/pulpcore
theme: readthedocs
DOCSYAML

# Building the bindings docs
mkdocs build

# Pack the built site.
tar cvf ${TEST_DIR}/core-python-client-docs.tar ./site
popd

pushd pulp_file-client
find ./docs/* -exec sed -i 's/Back to README/Back to HOME/g' {} \;
find ./docs/* -exec sed -i 's/README//g' {} \;
cp README.md docs/index.md
sed -i 's/docs\///g' docs/index.md
find ./docs/* -exec sed -i 's/\.md//g' {} \;

cat >> mkdocs.yml << DOCSYAML
---
site_name: PulpFile Client
site_description: File bindings
site_author: Pulp Team
site_url: https://docs.pulpproject.org/pulp_file_client/
repo_name: pulp/pulp_file
repo_url: https://github.com/pulp/pulp_file
theme: readthedocs
DOCSYAML

# Building the bindings docs
mkdocs build

# Pack the built site.
tar cvf ${TEST_DIR}/file-python-client-docs.tar ./site
popd

pushd pulp_certguard-client
find ./docs/* -exec sed -i 's/Back to README/Back to HOME/g' {} \;
find ./docs/* -exec sed -i 's/README//g' {} \;
cp README.md docs/index.md
sed -i 's/docs\///g' docs/index.md
find ./docs/* -exec sed -i 's/\.md//g' {} \;

cat >> mkdocs.yml << DOCSYAML
---
site_name: PulpCertguard Client
site_description: Certguard bindings
site_author: Pulp Team
site_url: https://docs.pulpproject.org/pulp_certguard_client/
repo_name: pulp/pulp_certguard
repo_url: https://github.com/pulp/pulp_certguard
theme: readthedocs
DOCSYAML

# Building the bindings docs
mkdocs build

# Pack the built site.
tar cvf ${TEST_DIR}/certguard-python-client-docs.tar ./site
popd

popd