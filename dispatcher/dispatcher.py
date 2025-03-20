import os
import sys

import click
import requests
import json
import yaml
from quixstreams import Application

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
    app = Application(
        broker_address=os.getenv("REDPANDA_BROKERS", "localhost:9092"),
        consumer_group="my-group",
    )
    messages_topic = app.topic(name="observation", value_serializer="json")
    errors_topic = app.topic(name=ERRORS_TOPIC, value_serializer="json")

    with app.get_producer() as producer:

        def on_update_callback(message: dict):
            message_type = message.get("message_type")
            if message_type not in message_registry.REGISTRY:
                logger.error(
                    "Message type not supported. Skipping. Check the message registry for supported events.",
                    extra={
                        "message_type": message_type,
                        "supported_message_types": list(
                            message_registry.REGISTRY.keys()
                        ),
                    },
                )

            logger.info(f"Processing event: {message_type}")
            try:
                # Dispatch to the function registered for this message type.
                message_registry.REGISTRY[message_type](message)
            except Exception as e:
                logger.error("Message could not be consumed", exc_info=True)
                error_payload = errors_topic.serialize(
                    value={"message": message, "error": str(e)}
                )
                producer.produce(topic=errors_topic.name, value=error_payload.value)

    # Create a streaming dataframe for the messages topic.
    sdf = app.dataframe(topic=messages_topic)
    sdf = sdf.update(on_update_callback)

    logger.info("Starting consumer")
    try:
        app.run()  # This call will block and process messages using your on_update_callback.
    except Exception as e:
        logger.exception("Error in application run", exc_info=True)


cli.add_command(auth)
cli.add_command(consume)


if __name__ == "__main__":
    cli()
