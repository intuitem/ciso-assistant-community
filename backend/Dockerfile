# syntax=docker/dockerfile:1
# Based on https://docs.docker.com/samples/django/

FROM python:3.11-alpine
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /code

# Configure locales
RUN apk update
RUN apk add --no-cache bash yaml-cpp
RUN apk add --no-cache py3-cffi libc-dev libffi-dev gcc python3-dev glib pango cairo
RUN apk add --no-cache musl musl-utils musl-locales tzdata lang
RUN apk add --no-cache gettext fontconfig ttf-freefont font-noto terminus-font libmagic1

COPY . /code/
COPY startup.sh /code/

RUN pip install --upgrade pip && \
    pip install -r requirements.txt


ENTRYPOINT ["bash", "startup.sh"]
EXPOSE 8000
