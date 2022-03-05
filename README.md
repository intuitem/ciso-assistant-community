# ASF Risk Manager

ASF RM offers a straightforward solution to centralize, assess and monitor your IT risks. What makes it special is the fact that it is based on field knowledge and inputs from security experts.

## General

TBD

## Requirements

- Python 3.8+
- pip 20.3+

## Quick Start

1. Clone the repository

```sh
$ git clone https://github.com/intuitem/asf-rm.git
$ cd asf-rm
```

2. Install docker and docker-compose if you don't have those.  [Read the official docs for your own OS/distro](https://docs.docker.com/get-docker/)

3. Once that is done, you can simply start-up ASF Risk Manager by running

```sh
$ docker-compose up
```

## Features

## How to set up ASF Risk Manager for development?

1. Clone the repository
```sh
$ git clone https://github.com/intuitem/asf-rm.git
$ cd asf-rm
```



2. Create a virtual environment with the tool of your choice and activate it. For instance:
```sh
$ pip install virtualenv
$ virtualenv venv
$ source venv/bin/activate
```

3. Install required dependencies
```sh
(venv)$ pip install -r requirements.txt
```

4. Setup secrets (env variable):

```sh
export DJANGO_SECRET_KEY=<>
```
make sure to keep the same one for the dev cycle otherwise some data could be compromised.

5. Setup Postgre database for development and provide the following env variables. Make sure to use a dedicated database as per Django recommendations:

```sh
export POSTGRES_NAME=<>
export POSTGRES_USER=<>
export POSTGRES_PASSWORD=<>
export DB_HOST=<>
```

1. Apply migrations. The first ones will init your database with the proper tables:
```sh
(venv)$ python manage.py migrate
```

6. Create a development Django user
```sh
(venv)$ python manage.py createsuperuser
```

7. Run development server

You may chose to run it dockerized or not.
```sh
(venv)$ docker-compose up
```
**OR**
```sh
(venv)$ python manage.py runserver
```

## Running the tests

After setting up your development environment, you may run tests:

```sh
(venv)$ python manage.py test <app_name>
```

## Structure

TBD

## Deployment

```sh
$ docker-compose -f docker-compose.prod.yml up
```

Do not forget to check the [Django Deployment checklist](https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/)

## Built With

- Django - Python Web Development Framework
- Gunicorn - Python WSGI HTTP Server for UNIX
- NGINX - HTTP Server and Reverse Proxy
- PostgreSQL - Open Source RDBMS
- Tailwind CSS - CSS Framework
- AlpineJS - Minimalist JS framework
- Docker - Container Engine

## Security

TBD

## License

GPLv3
