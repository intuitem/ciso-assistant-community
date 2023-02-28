# syntax=docker/dockerfile:1
# Based on https://docs.docker.com/samples/django/

FROM python:3.11
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /code
COPY requirements.txt /code/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN apt update && \
    apt install -y gettext && \
    apt install -y locales

COPY asf_rm /code/asf_rm
COPY cal /code/cal
COPY config /code/config
COPY core /code/core
COPY db/readme.txt /code/db/readme.txt
COPY iam /code/iam
COPY library /code/library
COPY locale /code/locale
COPY serdes /code/serdes
COPY staticfiles /code/staticfiles
COPY theme /code/theme
COPY tools /code/tools
COPY manage.py startup.sh /code/

RUN django-admin makemessages --all -i venv && \
    django-admin compilemessages -i venv

RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
    && sed -i -e 's/# fr_FR.UTF-8 UTF-8/fr_FR.UTF-8 UTF-8/' /etc/locale.gen \
    && locale-gen

ENTRYPOINT ["bash", "startup.sh"]
EXPOSE 8000
