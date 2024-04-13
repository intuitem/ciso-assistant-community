# syntax=docker/dockerfile:1
# Based on https://docs.docker.com/samples/django/

FROM python:3.11
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /code

# Remove Git installation steps since you will pass VERSION and BUILD as build-args

# Configure locales
RUN apt update && \
  apt install -y gettext locales && \
  apt clean && \
  rm -rf /var/lib/apt/lists/* && \
  sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
  sed -i -e 's/# fr_FR.UTF-8 UTF-8/fr_FR.UTF-8 UTF-8/' /etc/locale.gen && \
  locale-gen

COPY . /code/
COPY startup.sh /code/

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Define ARGs for VERSION and BUILD, which will be passed at build time
ARG VERSION=unknown
ARG BUILD=unknown

# Set the ARG values as ENV variables so they're available at runtime
ENV CISO_ASSISTANT_VERSION=$VERSION
ENV CISO_ASSISTANT_BUILD=$BUILD

ENTRYPOINT ["bash", "startup.sh"]
EXPOSE 8000
