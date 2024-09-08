# NOTE: this Dockerfile defines a steps that relies on buildkit.
# https://docs.docker.com/build/buildkit/

# may be built on bookworm, bullseye, buster, etc.
# or can be provided other base image for building
ARG BUILD_DEBIAN_VERSION=bookworm
ARG PYTHON_VERSION=3.11
ARG BUILD_IMAGE=python:${PYTHON_VERSION}-${BUILD_DEBIAN_VERSION}
# recommended to use slim for runtime; alpine should fix the pydantic_core
# see https://pkgs.alpinelinux.org/package/v3.20/community/x86/py3-pydantic-core
ARG PYTHON_RUNTIME_BASE=slim

FROM ${BUILD_IMAGE} as build

ARG PIP_CACHE_DIR=/tmp/pip-cache
ARG POETRY_CACHE_DIR=/tmp/poetry-cache
ARG POETRY_VERSION=1.8.3

WORKDIR /build

COPY pyproject.toml poetry.lock ./

# NOTE: mode is set to 0777 to avoid permission issues on MacOS local builds
RUN --mount=type=cache,mode=0777,target=${PIP_CACHE_DIR} \
    pip install --cache-dir ${PIP_CACHE_DIR} \
    poetry==${POETRY_VERSION}

RUN --mount=type=cache,mode=0777,target=${POETRY_CACHE_DIR} \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    poetry install \
    --no-dev \
    --no-interaction \
    --no-ansi \
    --no-root
# https://python-poetry.org/docs/configuration/#virtualenvscreate
# this creates a .venv/ directory in the project root (workdir)


### RUNTIME IMAGE ###
FROM python:${PYTHON_VERSION}-${PYTHON_RUNTIME_BASE} as runtime

ARG SOCKET_DIR=/www/run
RUN mkdir -p ${SOCKET_DIR}

ARG USER=1500
ARG GROUP=1500

ENV WORKDIR=/www/app
WORKDIR ${WORKDIR}

RUN addgroup --gid ${GROUP} app \
    && adduser --uid ${USER} --ingroup app --home ${WORKDIR} --shell /bin/sh --disabled-password app

RUN chown -R ${USER}:${GROUP} ${SOCKET_DIR}

USER ${USER}:${GROUP}

COPY --from=build --chown=${USER}:${GROUP} /build/.venv ./.venv

ENV PATH=${WORKDIR}/.venv/bin:${PATH}

COPY --chown=${USER}:${GROUP} . .
COPY --chown=${USER}:${GROUP} conf/uvicorn_logging.json /etc/uvicorn_logging.json
RUN chmod +x entrypoint.sh

ENV SOCKET_DIR=${SOCKET_DIR}
ENV SOCKET_NAME=app.sock
ENV RUN_MODE=socket

ENV PYTHONPATH=${WORKDIR}

VOLUME ${SOCKET_DIR}

ENTRYPOINT ["/www/app/entrypoint.sh"]
