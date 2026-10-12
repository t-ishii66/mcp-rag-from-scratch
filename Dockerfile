# Ubuntu for running and testing this project.
#
# Everything runs in here, so the host (macOS or otherwise) does not matter.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Be explicit about UTF-8. Without LANG, Python falls back to UTF-8 on its own
# (PEP 538), but that is a rescue, not a guarantee. Your own files in
# data/documents may hold non-ASCII text.
ENV LANG=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

# uv from the official image. It installs Python too.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Keep the virtualenv outside the bind mount, so it does not collide with the
# host's own .venv, which holds binaries built for the host.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    HF_HOME=/opt/hf-cache \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /workspace

# Install the dependencies first, so this layer stays cached.
#
# Copy uv.lock as well. Without it, what gets resolved here disagrees with the
# lock, and the later uv sync reinstalls everything (the layer grows from 9MB
# to 2.5GB).
#
# .python-version pins the interpreter. Without it uv takes the newest CPython
# it can find, and the build breaks whenever a release lands that the wheels
# do not cover yet.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --no-install-project

COPY . .
RUN uv sync

CMD ["bash"]
