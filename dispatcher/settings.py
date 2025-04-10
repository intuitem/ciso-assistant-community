import sys
import os
from pathlib import Path

import click
import yaml

from loguru import logger

log_message_format = (
    "<green>{time}</green> | <level>{level}</level> | <level>{message}</level>"
)

DEFAULT_CONFIG_PATH = ".dispatcher_config.yaml"


def load_yaml_config(config_path=DEFAULT_CONFIG_PATH):
    """Load configuration from a YAML file.

    Returns an empty dict if the file does not exist.
    """
    path = Path(config_path)
    if not path.exists():
        logger.warning(
            f"Config file '{config_path}' not found. You may want to run the init command."
        )
        return {}
    try:
        with path.open("r") as file:
            return yaml.safe_load(file) or {}
    except Exception as e:
        logger.error(f"Error loading config file: {e}")
        sys.exit(1)


def load_env_config():
    """Load configuration values from environment variables."""
    # Note: For booleans, we compare to the string "True"
    config = {
        "DEBUG": os.getenv("DEBUG", False),
        "rest": {
            "url": os.getenv("API_URL"),
            "verify_certificate": os.getenv("VERIFY_CERTIFICATE") == "True" or None,
        },
        "credentials": {
            "email": os.getenv("USER_EMAIL"),
            "password": os.getenv("USER_PASSWORD"),
        },
        "GLOBAL_FOLDER_ID": os.getenv("GLOBAL_FOLDER_ID"),
        "TOKEN": os.getenv("TOKEN"),
        "AUTO_RENEW_SESSION": os.getenv("AUTO_RENEW_SESSION") == "True" or None,
        "ERRORS_TOPIC": os.getenv("ERRORS_TOPIC"),
        "S3_URL": os.getenv("S3_URL"),
    }
    logger.trace("Loaded environment configuration", config=config)
    return config


def deep_merge(dict1, dict2):
    """
    Recursively merge dict2 into dict1.
    If keys conflict and both values are dictionaries, merge them recursively.
    Otherwise, dict2's value overwrites dict1's value,
    unless dict2's value is None—in which case, keep the original.
    Returns a new merged dictionary.
    """
    result = dict1.copy()
    for key, value in dict2.items():
        if value is None:
            # Skip None values so that file config is preserved.
            continue
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    logger.trace("Merged configuration", config=result)
    return result


def save_yaml_config(config, config_path=DEFAULT_CONFIG_PATH):
    """Save the configuration to a YAML file."""
    try:
        with open(config_path, "w") as file:
            yaml.safe_dump(config, file, default_flow_style=False, sort_keys=False)
        logger.info(
            f"Configuration saved to {config_path}. Please update it with your credentials."
        )
    except Exception as e:
        logger.error(f"Error saving config file: {e}")


@click.command()
@click.option("-y", is_flag=True, help="Automatically confirm configuration reset.")
def init_config(y):
    """Initialize (or reset) the configuration file using current environment settings."""
    env_conf = load_env_config()
    # Build a template configuration from env variables.
    template_config = {
        "rest": {
            "url": env_conf["rest"]["url"],
            "verify_certificate": env_conf["rest"]["verify_certificate"],
        },
        "credentials": env_conf["credentials"],
    }
    if y or click.confirm(
        f"This will create/reset '{DEFAULT_CONFIG_PATH}'. Do you wish to continue?"
    ):
        save_yaml_config(template_config, DEFAULT_CONFIG_PATH)


# Load configuration from YAML (if available)
file_config = load_yaml_config()

# Load configuration from environment variables
env_config = load_env_config()

# Merge both configurations with environment variables overriding file settings
config = deep_merge(file_config, env_config)

# Validate required settings
if "rest" not in config or "url" not in config["rest"]:
    logger.error(
        "API URL is missing in configuration. Check your config file or environment variables.",
        config=config,
    )
    sys.exit(1)
if (
    "credentials" not in config
    or not config["credentials"].get("email")
    or not config["credentials"].get("password")
):
    logger.error(
        "Missing credentials in configuration. Please set USER_EMAIL and USER_PASSWORD via environment variables or in the config file.",
        config=config,
    )
    # You might choose to exit here or allow CLI override

DEBUG = config.get("DEBUG", False)
API_URL = config.get("rest", {}).get("url", "https://localhost:8443")
VERIFY_CERTIFICATE = config.get("rest", {}).get("verify_certificate", True)
USER_EMAIL = config["credentials"].get("email", "user@company.org")
USER_PASSWORD = config["credentials"].get("password", "")
AUTO_RENEW_SESSION = config.get("AUTO_RENEW_SESSION", False)
ERRORS_TOPIC = config.get("ERRORS_TOPIC", "errors")
S3_URL = config.get("S3_URL", "http://localhost:9000")


def get_access_token(token_file=".tmp.yaml", token_env=os.getenv("TOKEN")):
    """Retrieve the access token from environment or a temporary YAML file."""
    if token_env:
        return token_env

    token_path = Path(token_file)
    if token_path.exists():
        try:
            with token_path.open("r") as file:
                auth_data = yaml.safe_load(file)
            return auth_data.get("token")
        except Exception as e:
            logger.error(f"Error reading token file: {e}")
            return None
    else:
        click.echo("Authentication data not found.", err=True)
        return None
