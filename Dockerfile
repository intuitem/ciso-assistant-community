# syntax=docker/dockerfile:1
# Based on https://docs.docker.com/samples/django/

FROM python:3.11
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE=1

ENV DJANGO_SECRET_KEY = ${DJANGO_SECRET_KEY}

ENV POSTGRES_NAME ${POSTGRES_NAME}
ENV POSTGRES_USER ${POSTGRES_USER}
ENV POSTGRES_PASSWORD ${POSTGRES_PASSWORD}
ENV DB_HOST ${DB_HOST}

WORKDIR /code
COPY requirements.txt /code/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN apt update && \
    apt install -y gettext && \
    apt install -y locales

COPY . /code/

RUN django-admin makemessages --all -i venv && \
    django-admin compilemessages -i venv

# RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
#     && sed -i -e 's/# fr_FR.UTF-8 UTF-8/fr_FR.UTF-8 UTF-8/' /etc/locale.gen \
#     && locale-gen

#RUN apt install -y npm && \
#     python manage.py tailwind build

RUN python manage.py collectstatic --no-input --clear

#CMD python manage.py runserver 0.0.0.0:8000
CMD ./startup.sh
EXPOSE 8000
