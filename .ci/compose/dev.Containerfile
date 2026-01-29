FROM pulp/pulp-ci-centos9:latest

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN echo 'eval "$(uv generate-shell-completion bash)"' >> ~/.bashrc
ENV UV_SYSTEM_PYTHON=1 UV_LINK_MODE=copy

# Install dependencies separate from source for better caching
WORKDIR /src
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=from=plugins,source=pulp_python/pyproject.toml,target=pulp_python/pyproject.toml \
    --mount=from=plugins,source=pulp_container/pyproject.toml,target=pulp_container/pyproject.toml \
    uv pip install \
      --group dev \
      -r pyproject.toml \
      -r pulp_python/pyproject.toml \
      -r pulp_container/pyproject.toml 

# Add source directories to container
COPY . pulpcore/
COPY --from=plugins pulp_python pulp_python/
COPY --from=plugins pulp_container pulp_container/

# Now install the plugins
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install \
      -e ./pulpcore \
      -e ./pulp_python \
      -e ./pulp_container 

WORKDIR /




USER pulp:pulp
RUN PULP_STATIC_ROOT=/var/lib/operator/static/ PULP_CONTENT_ORIGIN=localhost \
       /usr/local/bin/pulpcore-manager collectstatic --clear --noinput --link
USER root:root


RUN export plugin_path="$(uv pip show pulp_python | sed -n -e 's/Location: //p')/pulp_python" && \
    ln $plugin_path/app/webserver_snippets/nginx.conf /etc/nginx/pulp/pulp_python.conf || true
RUN export plugin_path="$(uv pip show pulp_container | sed -n -e 's/Location: //p')/pulp_container" && \
    ln $plugin_path/app/webserver_snippets/nginx.conf /etc/nginx/pulp/pulp_container.conf || true
