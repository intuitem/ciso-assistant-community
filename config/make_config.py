import questionary
from rich import print
import yaml
from jinja2 import Environment, FileSystemLoader

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


db = questionary.select("Choose a database", choices=["sqlite", "postgresql"]).ask()
print(mode, fqdn, port, db)
