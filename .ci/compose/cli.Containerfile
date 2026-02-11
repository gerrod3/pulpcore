FROM ghcr.io/pulp/base:latest
ARG CLI_VERSION
ADD https://github.com/pulp/pulp-cli.git#${CLI_VERSION} /pulp-cli

WORKDIR /pulp-cli
RUN pip install --no-cache-dir pulp-cli==${CLI_VERSION} -r test_requirements.txt

ARG PULP_API_ROOT
RUN pulp config create --base-url https://pulp --api-root "${PULP_API_ROOT}" --username "admin" --password "password"
RUN cp ~/.config/pulp/cli.toml tests/cli.toml

ARG TEST
COPY ${TEST}/pulp_webserver.crt /usr/local/share/ca-certificates/pulp_webserver.crt
RUN cat /usr/local/share/ca-certificates/pulp_webserver.crt >> $(python -c 'import certifi; print(certifi.where())')
RUN cat /usr/local/share/ca-certificates/pulp_webserver.crt >> $(python -c 'import ssl; print(ssl.get_default_verify_paths().openssl_cafile)')
RUN update-ca-trust
