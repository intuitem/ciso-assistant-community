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

COPY . /code/

ENTRYPOINT ["bash", "startup.sh"]
EXPOSE 8000
