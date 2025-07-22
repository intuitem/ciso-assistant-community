#! python3
import questionary
from rich import print
from jinja2 import Environment, FileSystemLoader
from icecream import ic
import os


def get_config():
    """Collect all configuration parameters from user"""
    config = {}

    # For local deployment, we only need limited configuration
    config["mode"] = questionary.select(
        "Deployment mode", choices=["local", "VM/Remote"], default="local"
    ).ask()
    config["can_do_tls"] = questionary.confirm(
        "Is the host internet-facing and can solve an ACME challenge for TLS?",
        default=False,
    ).ask()

    # Add custom certificate configuration
    if not config["can_do_tls"]:
        config["use_custom_cert"] = questionary.confirm(
            "Would you like to use custom certificates instead of self-signed?",
            default=False,
        ).ask()

        if config["use_custom_cert"]:
            config["cert_config"] = {
                "cert_path": questionary.path(
                    "Path to certificate file (relative to compose file): ",
                    default="./certs/cert.pem",
                ).ask(),
                "key_path": questionary.path(
                    "Path to private key file (relative to compose file): ",
                    default="./certs/key.pem",
                ).ask(),
            }

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
            "host": questionary.text(
                "Mailer host: ", default="host.docker.internal"
            ).ask(),
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
    env = Environment(loader=FileSystemLoader("templates"), autoescape=True)

    # Get template name based on database and proxy choice
    template_name = f"docker-compose-{config['db']}-{config['proxy']}.yml.j2"

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


def validate_cert_paths(config):
    """Validate that certificate files exist if custom certs are enabled"""
    if not config.get("can_do_tls") and config.get("use_custom_cert"):
        cert_path = config["cert_config"]["cert_path"]
        key_path = config["cert_config"]["key_path"]

        if not os.path.exists(cert_path):
            print(f"[red]Error: Certificate file not found at {cert_path}[/red]")
            return False

        if not os.path.exists(key_path):
            print(f"[red]Error: Private key file not found at {key_path}[/red]")
            return False

    return True


def main():
    print("[blue]CISO Assistant Docker Compose Configuration Builder[/blue]")

    config = get_config()
    ic(config)  # Debug output

    if not validate_cert_paths(config):
        print(
            "[red]Certificate validation failed. Please check the paths and try again.[/red]"
        )
        return

    generate_compose_file(config)

    print("[green]Successfully generated docker-compose.yml[/green]")

    # Show next steps
    print("\n[yellow]Next steps:[/yellow]")
    print("1. Review the generated docker-compose.yml file, and adjust it if needed")
    if config.get("use_custom_cert"):
        print("2. Ensure your certificate files are in place:")
        print(f"   - Certificate: {config['cert_config']['cert_path']}")
        print(f"   - Private key: {config['cert_config']['key_path']}")
    if config["db"] == "postgresql":
        print("3. Make sure PostgreSQL passwords are properly set")
    if config["need_mailer"]:
        print("4. Verify email configuration settings")
    print(
        f"5. Run './docker-compose.sh' and follow the instructions to create the first admin user"
    )
    print(f"6. Access the application at https://{config['fqdn']}:{config['port']}")


if __name__ == "__main__":
    main()
