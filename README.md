# MIRA

MIRA offers a straightforward solution to centralize, assess and monitor your IT risks. What makes it special is the fact that it is based on field knowledge and inputs from security experts.

## General

TBD

## Requirements

- Python 3.8+
- pip 20.3+

## Quick start

1. Clone the repository

```sh
$ git clone https://github.com/intuitem/asf-rm.git
$ cd asf-rm
```

2. Install docker and docker-compose if you don't have those.  [Read the official docs for your own OS/distro](https://docs.docker.com/get-docker/)

3. Once that is done, you can simply start-up MIRA by running

```sh
$ docker-compose up
```

## Features

## How to set up MIRA for development?

1. Clone the repository
```sh
$ git clone https://github.com/intuitem/asf-rm.git
$ cd asf-rm
```

2. Create local secret variables in a script located in parent folder (e.g. ../myvars)

```sh
export DJANGO_SECRET_KEY=<XXX>
export POSTGRES_NAME=asf
export POSTGRES_USER=asfuser
export POSTGRES_PASSWORD=<XXX>
export DB_HOST=localhost
```

3. Create a virtual environment with the tool of your choice and activate it. For instance:
```sh
$ pip install virtualenv
$ virtualenv venv
$ source venv/bin/activate
$ source ../myvars
```

4. Install required dependencies
```sh
(venv)$ pip install -r requirements.txt
```

5. Setup Postgres database for development and provide the following env variables. Make sure to use a dedicated database as per Django recommendations:


- Launch psql as superadmin
    - sudo su postgres
    - psql
- Create the database "asf"
    - create database asf;
- Create user "asfuser" and grant it access
    - create user asfuser with password '<POSTGRES_PASSWORD>';
    - grant all privileges on database asf to asfuser;


6. prepare migrations 

```sh
(venv)$ python manage.py makemigrations
```

7. Apply migrations. The first ones will init your database with the proper tables:
```sh
(venv)$ python manage.py migrate
```

8. Create a development Django user, that will be MIRA superuser
```sh
(venv)$ python manage.py createsuperuser
```

9. install Tailwind CSS

- npm install tailwindcss postcss postcss-import
- python manage.py tailwind install

10. Compile strings

- python3 manage.py compilemessages -l fr -i venv
- python3 manage.py compilemessages -l en -i venv


11. Run development server

You may chose to run it dockerized or not.
```sh
(venv)$ docker-compose up
```
**OR**
```sh
(venv)$ python manage.py runserver
```

## Running the tests

### Unit tests

After setting up your development environment, you may run tests:

```sh
(venv)$ bash test.sh
```
### Functional Tests

You can find details about functional tests into our [Functional Test Book](/asfTest/README.md).

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
