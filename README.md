# CISO Assistant

CISO Assistant brings a different take on Cyber Security Posture Management:

- by explicitly decoupling compliance from cybersecurity practices implementation
- providing simplified tools for decision making
- while providing capabilities for a program, product or an organization assessment against standard frameworks.
- you can bring your own framework as well using a simplified DSL

![](posture.png)

This decoupling allows you to save considerable amount of time:
- reuse previous assessments,
- assess a scope against multiple frameworks at the same time, 
- leave the reporting formatting and sanity check to CISO assistant and focus on your remediations

Read the [full article](https://intuitem.com/blog/we-are-going-open-source/) about the community editions on our blog.

## Supported frameworks

- ISO 27001
- NIST Cyber Security Framework (CSF) v1.1
- NIS2

Checkout the [library](/library/libraries/) for the Domain Specific Language used and how you can define your own.
### Coming soon

- CMMC
- GDPR checklist
- ANSSI CyberScore
- NIST CSF v2
## Community

Join our [open Discord community](https://discord.gg/qvkaMdQ8da) to interact with the team and other GRC experts.

## Installation

> The fastest and easiest way to get started is through the [free trial of cloud instance available here](https://intuitem.com/trial).

This part is divided in two sections, the quick start if you simply want to run CISO to see what it's made of, and the development setup if you want to go further.

### Requirements

- Python 3.8+
- pip 20.3+
- gettext 0.21+
- pango 1.0+

To install gettext and pango, do `sudo apt update && sudo apt install gettext libpangocairo-1.0-0 -y`

### Quick start 🚀

There are three methods to run CISO locally: using Python, using Docker or using docker-compose.

By default, Django secret key is generated randomly at each start of Mira. This is convenient for quick test, but not recommended for production, as it can break the sessions (see this [topic](https://stackoverflow.com/questions/15170637/effects-of-changing-djangos-secret-key) for more information). To set a fixed secret key, use the environment variable DJANGO_SECRET_KEY.

0. Clone the repository

```sh
git clone git@github.com:intuitem/ciso-assistant-community.git
cd ciso-assistant-community
```

#### Using Python

💡 *Advice*: run everything inside a virtual environment. It is a good practice concerning python projects!

Choose the tool of your choice, either python-venv or virtualenv. For example:

```sh
# Install python-venv
sudo apt install python-venv # or python3-venv
# Create the virtual environment venv
python -m venv venv # or python3 -m venv venv
# To enter inside the virtual environment
source venv/bin/activate
# If you want to exit the virtual environment once finished
deactivate
```

1. Install dependencies

```sh
pip install -r requirements.txt
```

2. Run migrations

```sh
python manage.py migrate
```

3. Collect static files

```sh
python manage.py collectstatic
```

4. Create your superuser

```sh
python manage.py createsuperuser
```

5. Run CISO Assistant

```sh
python manage.py runserver
```
You can then reach CISO Assistant using your web brower at [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

#### Using Docker

1. Upgrade or install docker and if you don't have it. [Read the official docs for your own OS/distro](https://docs.docker.com/get-docker/).

2. Build the image with an appropriate tag (e.g. *ciso-assistant:[version](ciso_assistant/VERSION)*), for example:

```sh
docker build . -t ciso-assistant:$(<ciso_assistant/VERSION)
```

3. Once this is done, you can simply start-up CISO by running:

```sh
docker run --rm -it --env CREATE_SUPERUSER=true -p 8000:8000 -v ./db:/code/db  ciso-assistant:$(<ciso_assistant/VERSION)
```

When asked for, enter your email and password for your superuser.

You can then reach CISO Assistant using your web brower at [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

For the following executions, simply run:

```sh
docker run --rm -p 8000:8000 -v ./db:/code/db  ciso-assistant:$(<ciso_assistant/VERSION)
```

⚠️ *WARNING*: If you're using WSL you'll need to activate *Systemd*. Check out this [topic](https://stackoverflow.com/questions/65400999/enable-systemd-in-wsl-2) to do it.


#### Using docker-compose with a Postgres database

Simply launch:
```sh
./docker-compose-pg.sh
```

When asked for, enter your email and password for your superuser.

You can then reach CISO Assistant using your web brower at [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

For the following executions, use "docker-compose up" directly.

### How to set up CISO Assistant for development? ✍️

1. Clone the repository.

```sh
git clone git@github.com:intuitem/ciso-assistant-community.git
cd ciso-assistant-community
```

2. Create a file in the parent folder (e.g. ../myvars) and store your environment variables within it by copying and modifying the following code and replace `"<XXX>"` by your private values. Take car not to commit this file in your git repo.

**Recommended variables**

```sh
export DJANGO_SECRET_KEY=<XXX>
export DJANGO_DEBUG=True

# Default url is set to http://127.0.0.1:8000 but you can change it, e.g. to use https with a caddy proxy
export CISO_URL=https://localhost:8443

# You can define the email of the first superuser
export CISO_SUPERUSER_EMAIL=<XXX>

# Setup a development mailer with Mailhog for example
export EMAIL_HOST_USER=''
export EMAIL_HOST_PASSWORD=''
export DEFAULT_FROM_EMAIL=ciso-assistant@ciso-assistantcloud.com
export EMAIL_HOST=localhost
export EMAIL_PORT=1025

```
> As said in the quickstart section, CISO Assistant generates a random Django secret key if not specified. To avoid broken sessions, it is preferable to set a fixed random value using the DJANGO_SECRET_KEY environment variable.

**Optional variables**

```sh
# CISO Assistant will use SQLite by default, but you can setup PostgreSQL by declaring these variables
export POSTGRES_NAME=ciso-assistant
export POSTGRES_USER=ciso-assistantuser
export POSTGRES_PASSWORD=<XXX>
export POSTGRES_PASSWORD_FILE=<XXX>  # alternative way to specify password
export DB_HOST=localhost
export DB_PORT=5432  # optional, default value is 5432

# Captcha, if you want to disable it just put empty strings
export RECAPTCHA_PUBLIC_KEY=<XXX>
export RECAPTCHA_PRIVATE_KEY=<XXX>

# Add a second backup mailer
export EMAIL_HOST_RESCUE=<XXX>
export EMAIL_PORT_RESCUE=587
export EMAIL_HOST_USER_RESCUE=<XXX>
export EMAIL_HOST_PASSWORD_RESCUE=<XXX>
export EMAIL_USE_TLS_RESCUE=True

# Idle session timeout management
export SESSION_COOKIE_AGE=900 # in seconds, (default 900, i.e. 15 minutes)
export SESSION_EXPIRE_AT_BROWSER_CLOSE=True # (default True)
export SESSION_SAVE_EVERY_REQUEST=True # (default True)
```

3. Choose the tool of your choice, either python-venv or virtualenv. For example:

```sh
# Install python-venv
sudo apt install python-venv # or python3-venv
# Create the virtual environment venv
python -m venv venv # or python3 -m venv venv
# To enter inside the virtual environment
source venv/bin/activate
# If you want to exit the virtual environment once finished
deactivate
```

4. Install required dependencies.

```sh
pip install -r requirements.txt
```

5. If you want to setup Postgres:

- Launch one of these commands to enter in Postgres:
  - ```psql as superadmin```
  - ```sudo su postgres```
  - ```psql```
- Create the database "ciso-assistant"
  - ```create database ciso-assistant;```
- Create user "ciso-assistantuser" and grant it access
  - ```create user ciso-assistantuser with password '<POSTGRES_PASSWORD>';```
  -  ```grant all privileges on database ciso-assistant to ciso-assistantuser;```

6. Prepare and apply migrations.

```sh
python manage.py makemigrations
python manage.py migrate
```

7. Create a superuser, that will be CISO administrator.

> If you have set a mailer and CISO_SUPERUSER_EMAIL variables, there's no need to create a Django superuser with createsuperuser, as it will be created automatically on first start. You should receive an email with a link to setup your password.

```sh
python manage.py createsuperuser
```

8. install Tailwind CSS.

```sh
npm install tailwindcss postcss postcss-import
python manage.py tailwind install
```

9. Compile strings.

```sh
python manage.py makemessages -i venv -l fr
python manage.py compilemessages -i venv -l fr
```

10. Run development server.

```sh
python manage.py runserver
```

11.   Configure the git hooks for generating the build name.

```sh
cd .git/hooks 
ln -fs ../../git_hooks/post-commit .
ln -fs ../../git_hooks/post-merge .
```

## Built With

- [Django](https://www.djangoproject.com/) - Python Web Development Framework
- [Gunicorn](https://gunicorn.org/) - Python WSGI HTTP Server for UNIX

- [PostgreSQL](https://www.postgresql.org/) - Open Source RDBMS
- [SQLite](https://www.sqlite.org/index.html) - Open Source RDBMS
- [Tailwind CSS](https://tailwindcss.com/) - CSS Framework
- [AlpineJS](https://alpinejs.dev/) - Minimalist JS framework
- [Docker](https://www.docker.com/) - Container Engine

## Security

Great care has been taken to follow security best practices. Please report any issue to security@intuitem.com.

## License

[AGPLv3](https://choosealicense.com/licenses/agpl-3.0/)
