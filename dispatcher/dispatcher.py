import os
import sys

import click
import requests
import json
import yaml
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import UnsupportedCodecError

from messages import message_registry
from settings import (
    API_URL,
    AUTO_RENEW_SESSION,
    DEBUG,
    VERIFY_CERTIFICATE,
    USER_EMAIL,
    USER_PASSWORD,
    ERRORS_TOPIC,
    init_config,
)

import utils.api as api

from loguru import logger

log_message_format = (
    "<green>{time}</green> | <level>{level}</level> | <level>{message}</level>"
)
if DEBUG:
    log_message_format += " | <magenta>{extra}</magenta>"

logger.remove(0)
logger.add(
    sys.stderr,
    format=log_message_format,
    colorize=True,
    backtrace=True,
    diagnose=True,
)

auth_data = dict()


@click.group()
def cli():
    """CLICA is the CLI tool to interact with CISO Assistant REST API."""
    pass


def _auth(email, password):
    """Authenticate to get a temp token (config file or params). Pass the email and password or set them on the config file"""
    url = f"{API_URL}/iam/login/"
    if email and password:
        data = {"username": email, "password": password}
    else:
        logger.info("trying credentials from the config file")
        if USER_EMAIL and USER_PASSWORD:
            data = {"username": USER_EMAIL, "password": USER_PASSWORD}
        else:
            logger.error("Could not find any usable credentials.")
            sys.exit(1)
    headers = {"accept": "application/json", "Content-Type": "application/json"}

    res = requests.post(url, json=data, headers=headers, verify=VERIFY_CERTIFICATE)
    if res.status_code == 200:
        with open(".tmp.yaml", "w") as yfile:
            yaml.safe_dump(res.json(), yfile)
            logger.success("Successfully authenticated. Token saved to .tmp.yaml")
        api.update_session_token()
    else:
        logger.error(
            "Check your credentials again. You can set them on the config file or on the command line.",
        )
        logger.error(res.json())


@click.command()
@click.option("--email", required=False)
@click.option("--password", required=False)
def auth(email: str, password: str):
    """Authenticate to get a temp token (config file or params). Pass the email and password or set them on the config file"""
    return _auth(email, password)


@click.command()
def consume():
    consumer = KafkaConsumer(
        # topic
        "observation",
        # consumer configs
        bootstrap_servers=os.getenv("BOOTSTRAP_SERVERS", "localhost:9092"),
        group_id="my-group",
        auto_offset_reset="earliest",
        # value_deserializer=lambda v: v,
    )

    error_producer = KafkaProducer(
        bootstrap_servers=os.getenv("BOOTSTRAP_SERVERS", "localhost:9092"),
    )

    try:
        logger.info("Starting consumer")
        for msg in consumer:
            logger.trace("Consumed record.", key=msg.key, value=msg.value)
            try:
                message = json.loads(msg.value.decode("utf-8"))
            except Exception as e:
                logger.error(f"Error decoding message: {e}")
                continue

            if message.get("message_type") not in message_registry.REGISTRY:
                logger.error(
                    "Message type not supported. Skipping. Check the message registry for supported events.",
                    message_type=message.get("message_type"),
                    supported_message_types=list(message_registry.REGISTRY.keys()),
                )
                continue

            logger.info(f"Processing event: {message.get('message_type')}")

            # Wrap the processing in a loop that allows for retries.
            while True:
                try:
                    message_registry.REGISTRY[message.get("message_type")](message)
                except requests.exceptions.RequestException as e:
                    logger.error("Request failed", response=e.response)
                    if e.response is not None:
                        logger.error(
                            f"Request failed with status code {e.response.status_code} and message: {e.response.text}"
                        )
                        if e.response.status_code == 401:
                            if not AUTO_RENEW_SESSION:
                                logger.error(
                                    "Session expired. Please run the `auth` command."
                                )
                                raise
                            try:
                                logger.debug(
                                    "Automatic session renewal enabled, attempting silent reauthentication."
                                )
                                _auth(USER_EMAIL, USER_PASSWORD)
                                continue
                            except Exception as e:
                                logger.error(
                                    "Silent reauthentication failed. Please run the `auth` command.",
                                    e,
                                )
                                raise

                except Exception as e:
                    # NOTE: This exception is necessary to avoid the dispatcher stopping and not consuming any more messages.
                    logger.exception("Message could not be consumed")
                    error_producer.send(
                        ERRORS_TOPIC,
                        value=json.dumps(
                            {"message": message, "error": str(e)}
                        ).encode(),
                    )
                    break  # break out of retry loop; we don't want to retry on non-request errors
                else:
                    # Processing succeeded; break out of the retry loop.
                    break

    except UnsupportedCodecError as e:
        logger.exception("KO", e)
    except Exception as e:
        logger.exception("KO", e)
        # raise e
    finally:
        error_producer.flush()
        error_producer.close()


cli.add_command(auth)
cli.add_command(consume)
cli.add_command(init_config)


if __name__ == "__main__":
    cli()
