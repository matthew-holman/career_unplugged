FROM python:3.9-slim

ENV PYTHONPATH=${PYTHONPATH}:.
ENV POETRY_VERSION=1.4.0

RUN pip install "poetry==$POETRY_VERSION"
RUN poetry config virtualenvs.create false

ARG TARGET_ENV='local-dev'
ENV TARGET_ENV=$TARGET_ENV

RUN apt-get update && apt -y install libpq-dev python3-dev gcc postgresql awscli make

WORKDIR /api/

COPY .env *.py Makefile alembic.ini pyproject.toml poetry.lock setup.cfg ./

COPY ./alembic ./alembic
COPY ./app ./app
COPY ./tests ./tests

EXPOSE 8000
RUN make requirements

RUN rm -rf /tmp && rm -rf .cache

RUN useradd -d /home/matthewh -m -s /bin/bash matthewh
USER matthewh
