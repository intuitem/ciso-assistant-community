#! python3
import questionary
from rich import print
import yaml
from jinja2 import Environment, FileSystemLoader
from icecream import ic

mode = questionary.select(
    "What is your deployment mode?", choices=["local", "VM/remote"], default="local"
).ask()

fqdn = "localhost"
port = "8443"
if mode != "local":
    fqdn = questionary.text(
        "Expected FQDN/hostname", default="ciso.assistant.local"
    ).ask()
port = questionary.text("Port to use", default="8443").ask()

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
    EMAIL_HOST = questionary.text("Mailer host: ", default="localhost").ask()
    EMAIL_PORT = questionary.text("Mailer port: ", default="1025").ask()
    EMAIL_USE_TLS = questionary.confirm("Use TLS? ", default=False).ask()
    EMAIL_HOST_USER = questionary.text("Mailer username: ").ask()
    EMAIL_HOST_PASSWORD = questionary.password("Mailer password: ").ask()
    DEFAULT_FROM_EMAIL = questionary.text(
        "Default from email: ", default="ciso-assistant@company.com"
    ).ask()

db = questionary.select(
    "Choose a database", choices=["sqlite", "postgresql"], default="sqlite"
).ask()

# PostgreSQL configuration
POSTGRES_NAME = ""
POSTGRES_USER = ""
POSTGRES_PASSWORD = ""
DB_HOST = ""
DB_PORT = ""
POSTGRES_PASSWORD_FILE = None

if db == "postgresql":
    POSTGRES_NAME = questionary.text("Database name: ", default="ciso-assistant").ask()
    POSTGRES_USER = questionary.text(
        "Database user: ", default="ciso-assistantuser"
    ).ask()
    use_password_file = questionary.confirm(
        "Use password file instead of direct password?", default=False
    ).ask()

    if use_password_file:
        POSTGRES_PASSWORD_FILE = questionary.path(
            "Path to PostgreSQL password file: "
        ).ask()
    else:
        POSTGRES_PASSWORD = questionary.password("Database password: ").ask()

    DB_HOST = questionary.text("Database host: ", default="localhost").ask()
    DB_PORT = questionary.text("Database port: ", default="5432").ask()

proxy = questionary.select(
    "Choose a proxy", choices=["Caddy", "Traefik"], default="Caddy"
).ask()

custom_certificate = questionary.confirm(
    "Do you need to include custom certificate? Paths will be needed", default=False
).ask()

cert_file = None
key_file = None
if custom_certificate:
    cert_file = questionary.path("Path to cert file").ask()
    key_file = questionary.path("Path to key file").ask()

enable_debug = questionary.confirm("Enable debug mode?", default=False).ask()

ic(
    mode,
    fqdn,
    port,
    db,
    need_mailer,
    proxy,
    custom_certificate,
    cert_file,
    key_file,
    enable_debug,
    EMAIL_HOST,
    EMAIL_PORT,
    EMAIL_USE_TLS,
    EMAIL_HOST_USER,
    EMAIL_HOST_PASSWORD,
    DEFAULT_FROM_EMAIL,
)

if db == "postgresql":
    ic(
        POSTGRES_NAME,
        POSTGRES_USER,
        POSTGRES_PASSWORD_FILE,
        POSTGRES_PASSWORD,
        DB_HOST,
        DB_PORT,
    )
