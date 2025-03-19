import os
import sys

import click
import requests
import json
import yaml
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import UnsupportedCodecError

from messages import message_registry
from settings import API_URL, VERIFY_CERTIFICATE, EMAIL, PASSWORD, ERRORS_TOPIC

from loguru import logger

logger.remove(0)
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD at HH:mm:ss}</green> | <level>{level}</level> | <level>{message}</level> | <magenta>{extra}</magenta>",
    colorize=True,
    backtrace=True,
    diagnose=True,
)

auth_data = dict()


@click.group()
def cli():
    """CLICA is the CLI tool to interact with CISO Assistant REST API."""
    pass


@click.command()
@click.option("--email", required=False)
@click.option("--password", required=False)
def auth(email, password):
    """Authenticate to get a temp token (config file or params). Pass the email and password or set them on the config file"""
    url = f"{API_URL}/iam/login/"
    if email and password:
        data = {"username": email, "password": password}
    else:
        logger.info("trying credentials from the config file")
        if EMAIL and PASSWORD:
            data = {"username": EMAIL, "password": PASSWORD}
        else:
            logger.error("Could not find any usable credentials.")
            sys.exit(1)
    headers = {"accept": "application/json", "Content-Type": "application/json"}

    res = requests.post(url, json=data, headers=headers, verify=VERIFY_CERTIFICATE)
    if res.status_code == 200:
        with open(".tmp.yaml", "w") as yfile:
            yaml.safe_dump(res.json(), yfile)
            logger.info("Looks good, you can move to other commands.")
    else:
        logger.error(
            "Check your credentials again. You can set them on the config file or on the command line.",
        )
        logger.error(res.json())


@click.command()
def consume():
    consumer = KafkaConsumer(
        # topic
        "observation",
        # consumer configs
        bootstrap_servers=os.getenv("REDPANDA_BROKERS", "localhost:9092"),
        group_id="my-group",
        auto_offset_reset="earliest",
        # value_deserializer=lambda v: v,
    )

    error_producer = KafkaProducer(
        bootstrap_servers=os.getenv("REDPANDA_BROKERS", "localhost:9092"),
    )

    try:
        logger.info("Starting consumer")
        for msg in consumer:
            logger.trace("Consumed record.", key=msg.key, value=msg.value)
            try:
                message = json.loads(msg.value.decode("utf-8"))
            except Exception as e:
                logger.error(f"Error decoding message: {e}")
            else:
                if message.get("message_type") not in message_registry.REGISTRY:
                    logger.error(
                        "Message type not supported. Skipping. Check the message registry for supported events.",
                        message_type=message.get("message_type"),
                        supported_message_types=list(message_registry.REGISTRY.keys()),
                    )
                    continue
                logger.info(f"Processing event: {message.get('message_type')}")
                try:
                    message_registry.REGISTRY[message.get("message_type")](message)
                except Exception as e:
                    # NOTE: This exception is necessary to avoid the dispatcher stopping and not consuming any more messages.
                    # TODO: Message-bound error handling is to be done here.
                    logger.error("KO", e)
                    error_producer.send(ERRORS_TOPIC, key=msg.key, value=msg.value)

    except UnsupportedCodecError as e:
        logger.error("KO", e)
    except Exception as e:
        logger.error("KO", e)
        # raise e
    finally:
        error_producer.flush()
        error_producer.close()


cli.add_command(auth)
cli.add_command(consume)


if __name__ == "__main__":
    cli()
