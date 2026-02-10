TEST ?= pulp
TEST_DIR = .ci/compose/$(TEST)
SETTINGS_FILE = $(TEST_DIR)/settings.py
SCRIPTS_DIR = .ci/compose/scripts

build:
	python3 -m build
	twine check dist/*

PACKAGE ?= dist/pulpcore-*-py3-none-any.whl
install:
	pip install $(PACKAGE) -c .ci/assets/ci_constraints.txt


OPENAPI_ENV = DJANGO_SETTINGS_MODULE=pulpcore.app.settings PULP_SETTINGS=$(SETTINGS_FILE)
openapi:
	$(OPENAPI_ENV) pulpcore-manager openapi --file $(TEST_DIR)/api.json
	$(OPENAPI_ENV) pulpcore-manager openapi --bindings --component "core" --file $(TEST_DIR)/core-api.json
	$(OPENAPI_ENV) pulpcore-manager openapi --bindings --component "file" --file $(TEST_DIR)/file-api.json
	$(OPENAPI_ENV) pulpcore-manager openapi --bindings --component "certguard" --file $(TEST_DIR)/certguard-api.json

GENERATOR_DIR ?= ../pulp-openapi-generator
CLIENT_TYPE ?= python
bindings:
	$(SCRIPTS_DIR)/build_client.sh $(TEST) $(CLIENT_TYPE) $(GENERATOR_DIR)

bindings-docs:
	$(SCRIPTS_DIR)/build_client_docs.sh $(TEST) $(CLIENT_TYPE) $(GENERATOR_DIR)

test-setup:
	$(SCRIPTS_DIR)/setup.sh $(TEST)

test-install:
	$(SCRIPTS_DIR)/install.sh $(TEST)

test:
	$(SCRIPTS_DIR)/test.sh $(TEST)

ci-build: build install openapi bindings bindings-docs

ci-test: test-setup test-install test

ci: ci-build ci-test