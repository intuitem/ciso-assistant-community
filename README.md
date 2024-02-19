# CISO Assistant

![](gh_banner.png)

CISO Assistant brings a different take on Cyber Security Posture Management:

- by explicitly decoupling compliance from cybersecurity practices implementation
- providing simplified tools for decision making
- while providing capabilities for a program, product or an organization assessment against standard frameworks.
- you can bring your own framework as well using a simplified DSL
- aim to be a one stop shop for cyber security management and cover the layers of GRC (Governance, Risk and Compliance)

![](posture.png)

This decoupling allows you to save considerable amount of time:
- reuse previous assessments,
- assess a scope against multiple frameworks at the same time, 
- leave the reporting formatting and sanity check to CISO assistant and focus on your remediations

Read the [full article](https://intuitem.com/blog/we-are-going-open-source/) about the community editions on our blog.

## Supported frameworks

- ISO 27001:2022
- NIST Cyber Security Framework (CSF) v1.1
- NIS2
- SOC2
- PCI DSS 4.0
- CMMC v2
- PSPF

Checkout the [library](/library/libraries/) for the Domain Specific Language used and how you can define your own.
### Coming soon

- GDPR checklist
- ANSSI CyberScore
- DFS 500
- DORA
- and much more!

### Add your own framework

Have a look in the tools directory and its dedicated readme. The convert_framework.py script will help you create your library from a simple Excel file.

## Community

Join our [open Discord community](https://discord.gg/qvkaMdQ8da) to interact with the team and other GRC experts.

## Testing in the cloud

> The fastest and easiest way to get started is through the [free trial of cloud instance available here](https://intuitem.com/trial).

## Testing locally - Quick start 🚀

To run CISO Assistant locally in a straightforward way, you can use Docker compose.

1. Clone the repository

```sh
git clone git@github.com:intuitem/ciso-assistant-community.git
cd ciso-assistant-community
```

2. Launch docker-compose script

```sh
./docker-compose.sh
```

When asked for, enter your email and password for your superuser.

You can then reach CISO Assistant using your web brower at [https://localhost:8443/](https://localhost:8443/)

For the following executions, use "docker-compose up" directly.

## Setting up CISO Assistant for development

### Requirements

- Python 3.11+
- pip 20.3+
- npm 10.2+

### Running the backend

1. Clone the repository.

```sh
git clone git@github.com:intuitem/ciso-assistant-community.git
cd ciso-assistant-community
```

2. Create a file in the parent folder (e.g. ../myvars) and store your environment variables within it by copying and modifying the following code and replace `"<XXX>"` by your private values. Take care not to commit this file in your git repo.

**Mandatory variables**

All variables in the backend have handy default values.

**Recommended variables**

```sh
export DJANGO_DEBUG=True

# Default url is set to http://localhost:5173 but you can change it, e.g. to use https with a caddy proxy
export CISO_ASSISTANT_URL=https://localhost:8443

# Setup a development mailer with Mailhog for example
export EMAIL_HOST_USER=''
export EMAIL_HOST_PASSWORD=''
export DEFAULT_FROM_EMAIL=ciso-assistant@ciso-assistantcloud.com
export EMAIL_HOST=localhost
export EMAIL_PORT=1025
```

**Other variables**

```sh
# CISO Assistant will use SQLite by default, but you can setup PostgreSQL by declaring these variables
export POSTGRES_NAME=ciso-assistant
export POSTGRES_USER=ciso-assistantuser
export POSTGRES_PASSWORD=<XXX>
export POSTGRES_PASSWORD_FILE=<XXX>  # alternative way to specify password
export DB_HOST=localhost
export DB_PORT=5432  # optional, default value is 5432

# Add a second backup mailer
export EMAIL_HOST_RESCUE=<XXX>
export EMAIL_PORT_RESCUE=587
export EMAIL_HOST_USER_RESCUE=<XXX>
export EMAIL_HOST_PASSWORD_RESCUE=<XXX>
export EMAIL_USE_TLS_RESCUE=True

# You can define the email of the first superuser, useful for automation
export CISO_SUPERUSER_EMAIL=<XXX>

# By default, Django secret key is generated randomly at each start of CISO Assistant. This is convenient for quick test, 
# but not recommended for production, as it can break the sessions (see 
# this [topic](https://stackoverflow.com/questions/15170637/effects-of-changing-djangos-secret-key) for more information). 
# To set a fixed secret key, use the environment variable DJANGO_SECRET_KEY.
export DJANGO_SECRET_KEY=...
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

6. Apply migrations.

```sh
python manage.py migrate
```

7. Create a Django superuser, that will be CISO Assistant administrator.

> If you have set a mailer and CISO_SUPERUSER_EMAIL variable, there's no need to create a Django superuser with createsuperuser, as it will be created automatically on first start. You should receive an email with a link to setup your password.

```sh
python manage.py createsuperuser
```

8.  Run development server.

```sh
python manage.py runserver
```

9.   Configure the git hooks for generating the build name.

```sh
cd .git/hooks 
ln -fs ../../git_hooks/post-commit .
ln -fs ../../git_hooks/post-merge .
```

### Running the frontend

1. cd into the frontend directory

```shell
cd frontend
```

2. Declare the PUBLIC_BACKEND_API_URL environment variable.

EITHER

```bash
echo "PUBLIC_BACKEND_API_URL=http://localhost:8000/api" > .env
```

OR

```bash
export PUBLIC_BACKEND_API_URL=http://localhost:8000/api
```
Note: for docker compose, or if you use a proxy like caddy, the ORIGIN variable has to be declared too (see https://kit.svelte.dev/docs/configuration#csrf).


3. Install dependencies

```bash
npm install
```

4. Start a development server (make sure that the django app is running)

```bash
npm run dev
```

5. Reach the frontend on http://localhost:5173

Note: Safari will not properly work in this setup, as it requires https for secure cookies. The simplest solution is to use Chrome or Firefox. An alternative is to use a caddy proxy. This is the solution used in docker-compose, so you can use it as an example.

## Managing migrations

The migrations are tracked by version control, https://docs.djangoproject.com/en/4.2/topics/migrations/#version-control

For the first version of the product, it is recommended to start from a clean migration.

Note: to clean existing migrations, type:

```sh
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc"  -delete
```

After a change (or a clean), it is necessary to re-generate migration files:

```sh
python manage.py makemigrations
python manage.py migrate
```

These migration files should be tracked by version control.

## Built With

- [Django](https://www.djangoproject.com/) - Python Web Development Framework
- [Gunicorn](https://gunicorn.org/) - Python WSGI HTTP Server for UNIX

- [PostgreSQL](https://www.postgresql.org/) - Open Source RDBMS
- [SQLite](https://www.sqlite.org/index.html) - Open Source RDBMS
- [SvelteKit](https://kit.svelte.dev/) - Frontend framework
- [Docker](https://www.docker.com/) - Container Engine

## Security

Great care has been taken to follow security best practices. Please report any issue to security@intuitem.com.

## License

[AGPLv3](https://choosealicense.com/licenses/agpl-3.0/)
