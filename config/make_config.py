import questionary
from rich import print
import yaml
from jinja2 import Environment, FileSystemLoader
from icecream import ic

mode = questionary.select(
    "What is your deployment mode?", choices=["local", "VM/remote"]
).ask()

fqdn = "localhost"
port = "8443"

if mode != "local":
    fqdn = questionary.text(
        "Expected FQDN/hostname", default="ciso.assistant.local"
    ).ask()
    port = questionary.text("Port to use", default="443").ask()

need_mailer = questionary.confirm(
    "Do you need email notifications? Mailer settings will be required", default=False
).ask()

EMAIL_HOST = ""
EMAIL_PORT = ""
EMAIL_USE_TLS = ""
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
DEFAULT_FROM_EMAIL = ""

if need_mailer:
    """
    export EMAIL_HOST_USER=''
    export EMAIL_HOST_PASSWORD=''
    export DEFAULT_FROM_EMAIL=ciso-assistant@ciso-assistantcloud.com
    export EMAIL_HOST=localhost
    export EMAIL_PORT=1025
    export EMAIL_USE_TLS=True
    """
    EMAIL_HOST = questionary.text("Mailer host: ", default="localhost").ask()
    EMAIL_PORT = questionary.text("Mailer port: ", default="1025").ask()
    EMAIL_USE_TLS = questionary.confirm("Use TLS? ", default=False).ask()
    EMAIL_HOST_USER = questionary.text("Mailer username: ").ask()
    EMAIL_HOST_PASSWORD = questionary.password("Mailer password: ").ask()
    DEFAULT_FROM_EMAIL = questionary.text(
        "Default from email: ", default="ciso-assistant@company.com"
    ).ask()
db = questionary.select("Choose a database", choices=["sqlite", "postgresql"]).ask()
ic(
    mode,
    fqdn,
    port,
    db,
    need_mailer,
    EMAIL_HOST,
    EMAIL_PORT,
    EMAIL_USE_TLS,
    EMAIL_HOST_USER,
    EMAIL_HOST_PASSWORD,
    DEFAULT_FROM_EMAIL,
)
"""
export POSTGRES_NAME=ciso-assistant
export POSTGRES_USER=ciso-assistantuser
export POSTGRES_PASSWORD=<XXX>
export POSTGRES_PASSWORD_FILE=<XXX>  # alternative way to specify password
export DB_HOST=localhost
export DB_PORT=5432  # optional, default value is 5432
"""
