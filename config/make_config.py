#! python3
import questionary
from rich import print
import yaml
from jinja2 import Environment, FileSystemLoader
from icecream import ic


def get_config():
    """Collect all configuration parameters from user"""
    config = {}

    # For local deployment, we only need limited configuration
    config["mode"] = "local"  # Fixed to local for now

    # FQDN/hostname selection
    config["fqdn"] = questionary.text(
        "Expected FQDN/hostname.\nIf you are planning to host this on a VM/remote host and access it elsewhere, make sure to set this accordingly and handle the DNS resolution (eg. /etc/hosts)",
        default="localhost",
    ).ask()

    config["port"] = questionary.text("Port to use", default="8443").ask()

    # Database selection and configuration
    config["db"] = questionary.select(
        "Choose a database", choices=["sqlite", "postgresql"], default="sqlite"
    ).ask()

    if config["db"] == "postgresql":
        config["postgres"] = {
            "name": questionary.text("Database name: ", default="ciso_assistant").ask(),
            "user": questionary.text("Database user: ", default="ciso_assistant").ask(),
            "password": questionary.password(
                "Database password: ", default="ciso_assistant"
            ).ask(),
        }

    # Proxy selection
    config["proxy"] = questionary.select(
        "Choose a proxy", choices=["caddy", "traefik"], default="caddy"
    ).ask()

    # Email configuration
    config["need_mailer"] = questionary.confirm(
        "Do you need email notifications? Mailer settings will be required",
        default=False,
    ).ask()

    if config["need_mailer"]:
        config["email"] = {
            "host": questionary.text("Mailer host: ", default="localhost").ask(),
            "port": questionary.text("Mailer port: ", default="1025").ask(),
            "use_tls": questionary.confirm("Use TLS? ", default=False).ask(),
            "user": questionary.text("Mailer username: ").ask(),
            "password": questionary.password("Mailer password: ").ask(),
            "from_email": questionary.text(
                "Default from email: ", default="ciso-assistant@company.com"
            ).ask(),
        }

    # Debug mode for local development
    config["enable_debug"] = questionary.confirm(
        "Enable debug mode?", default=True if config["db"] == "sqlite" else False
    ).ask()

    return config


def generate_compose_file(config):
    """Generate docker-compose.yml based on configuration"""
    env = Environment(loader=FileSystemLoader("templates"))

    # Get template name based on database and proxy choice
    template_name = f"docker-compose-local-{config['db']}-{config['proxy']}.yml.j2"

    try:
        template = env.get_template(template_name)
    except Exception as e:
        print(f"[red]Error: Template {template_name} not found![/red]")
        print(
            f"[yellow]Please ensure you have the following template file in your templates directory:[/yellow]"
        )
        print(f"[yellow]templates/{template_name}[/yellow]")
        print(
            f"[yellow]Expected template name format: docker-compose-local-<db>-<proxy>.yml.j2[/yellow]"
        )
        print(f"[yellow]Where <db> is one of: sqlite, postgresql[/yellow]")
        print(f"[yellow]And <proxy> is one of: caddy, traefik[/yellow]")
        raise e

    # Render template with configuration
    compose_content = template.render(config)

    # Write to docker-compose.yml
    with open("docker-compose.yml", "w") as f:
        f.write(compose_content)


def main():
    print("[blue]CISO Assistant Docker Compose Configuration Builder[/blue]")
    print("[yellow]Local Deployment Configuration[/yellow]")

    config = get_config()
    ic(config)  # Debug output
    generate_compose_file(config)

    print("[green]Successfully generated docker-compose.yml[/green]")

    # Show next steps
    print("\n[yellow]Next steps:[/yellow]")
    print("1. Review the generated docker-compose.yml file")
    if config["db"] == "postgresql":
        print("2. Make sure PostgreSQL passwords are properly set")
    if config["need_mailer"]:
        print("3. Verify email configuration settings")
    print(f"4. Run 'docker compose up -d' to start the services")
    print(f"5. Access the application at https://{config['fqdn']}:{config['port']}")


if __name__ == "__main__":
    main()
