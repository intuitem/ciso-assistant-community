# MIRA

MIRA offers a straightforward security_function to centralize, assess and monitor your IT risks. What makes it special is the fact that it is based on field knowledge and inputs from security experts.

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

2. Create local secret variables in a script located in parent folder (e.g. ../myvars), to be adapted

```sh
export DJANGO_SECRET_KEY=<XXX>
export DJANGO_DEBUG=True
export DJANGO_SUPERUSER_PASSWORD=<XXX>
export MIRA_DOMAIN=mira.alsigo.net
# for postgres (if the variables are not defined then we use sqlite)
export POSTGRES_NAME=asf
export POSTGRES_USER=asfuser
export POSTGRES_PASSWORD=<XXX>
export DB_HOST=localhost
export DB_PORT=5432
# Mailing in production with gmail for example
export EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
export EMAIL_HOST=smtp.gmail.com
export EMAIL_USE_TLS=True
export EMAIL_PORT=587
export EMAIL_HOST_USER=your_account@gmail.com
export EMAIL_HOST_PASSWORD=yourpassword
export DEFAULT_FROM_EMAIL=mira@alsigo.net
export PROTOCOL=https
# Mailing in development with Mailhog for example
export EMAIL_HOST=localhost
export EMAIL_PORT=1025
export PROTOCOL=http
```

NOTE: DB_PORT is optional, and defaults to 5432.

NOTE: To use the `reset.sh` script, you need to set the `POSTGRES_DBLOGIN` variable to the login of the postgres daemon.

3. Create a virtual environment with the tool of your choice and activate it. For scenario:
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

- Note: to clean existing migrations, type:
```sh
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc"  -delete
```

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

- python3 manage.py makemessages -i venv -l fr
- python3 manage.py compilemessages -i venv -l fr


11. Run development server

You may chose to run it dockerized or not.
```sh
$ docker-compose up
```
**OR**
```sh
(venv)$ python manage.py runserver
```

12. Configure the git hooks for generating the build name

```sh
(venv)$ cd .git/hooks 
(venv)$ ln -fs ../../git_hooks/post-commit .
(venv)$ ln -fs ../../git_hooks/post-merge .
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

## Deployment with docker

```sh
$ docker-compose -f docker-compose.prod.yml up
```

Do not forget to check the [Django Deployment checklist](https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/)

## Deployement with K8s

The docker image must be compiled with:
```sh
$ docker build -t mira:x.y.z .
```
The image must be then tagged "mira:latest" for the appropriate repository and pushed to it.

The deployment with sqlite is very simple:
- Environment variables are defined in cm.mira-config-dev.yaml (except secrets)
- Secrets shall be created using the create_secret.py script on a list of exports (eg. myvars) and then "kubectl create secrets" as recommended by the script
- A service called "mira" is defined in svc.mira.yaml
- An ingress is defined in ing.mira.yaml. It shall be adapted to the served domain.
- The pods can be created with sts.mira.yaml, using a StatefulSet.

When using Postgres, the pods can be created with deploy.mira.yaml, using a Deployement.

Configurations and readme can be found in the k8s directory, in particular for Scaleway. 

## Built With

- Django - Python Web Development Framework
- Gunicorn - Python WSGI HTTP Server for UNIX
- caddy - HTTP Server and Reverse Proxy
- PostgreSQL - Open Source RDBMS
- sqlite - Open Source RDBMS
- Tailwind CSS - CSS Framework
- AlpineJS - Minimalist JS framework
- Docker - Container Engine

## Security

TBD

## License

GPLv3
