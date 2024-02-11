# syntax=docker/dockerfile:1
# Based on https://docs.docker.com/samples/django/

FROM python:3.11
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /code
COPY . /code/
COPY startup.sh /code/

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN apt update && \
  apt install -y gettext && \
  apt install -y locales

RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
  && sed -i -e 's/# fr_FR.UTF-8 UTF-8/fr_FR.UTF-8 UTF-8/' /etc/locale.gen \
  && locale-gen

ENTRYPOINT ["bash", "startup.sh"]
EXPOSE 8000
