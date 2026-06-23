import sys

import click
import requests
import json
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable, UnsupportedCodecError

from messages import message_registry
import settings
from settings import init_config

import utils.api as api

from loguru import logger

from utils.kafka import build_kafka_config


log_message_format = (
    "<green>{time}</green> | <level>{level}</level> | <level>{message}</level>"
)
if settings.DEBUG:
    log_message_format += " | <magenta>{extra}</magenta>"

logger.remove()
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
    """The CISO Assistant dispatcher is a command line tool that consumes messages from a Kafka topic and processes them."""
    pass


@click.command()
def consume():
    """
    Consume messages from the Kafka topic and process them.
    """
    api.update_session_token()
    kafka_cfg = build_kafka_config()
    logger.info("Starting consumer", bootstrap_servers=settings.BOOTSTRAP_SERVERS)
    try:
        consumer = KafkaConsumer(
            # topic
            "observation",
            # consumer configs
            group_id="my-group",
            auto_offset_reset="earliest",
            **kafka_cfg,
            # value_deserializer=lambda v: v,
        )
    except NoBrokersAvailable as e:
        logger.error(
            "No brokers available. Please check your Kafka configuration and make sure your broker is running",
            bootstrap_servers=settings.BOOTSTRAP_SERVERS,
            error=e,
        )
        sys.exit(1)

    logger.info("Starting producer", bootstrap_servers=settings.BOOTSTRAP_SERVERS)
    try:
        error_producer = KafkaProducer(
            **kafka_cfg,
        )
    except NoBrokersAvailable as e:
        logger.error(
            "No brokers available. Please check your Kafka configuration and make sure your broker is running",
            bootstrap_servers=settings.BOOTSTRAP_SERVERS,
            error=e,
        )
        sys.exit(1)

    try:
        logger.info(
            f"Dispatcher up and running {'(authenticated)' if kafka_cfg.get('security_protocol') else '(unauthenticated)'}",
        )
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
                            logger.error(
                                "Authentication failed (401). The access token is invalid or expired. "
                                "Provision a new Personal Access Token in CISO Assistant and update USER_TOKEN."
                            )
                            raise
                        raise

                except Exception as e:
                    # NOTE: This exception is necessary to avoid the dispatcher stopping and not consuming any more messages.
                    logger.exception("Message could not be consumed")
                    error_producer.send(
                        settings.ERRORS_TOPIC,
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
        consumer.close()
        error_producer.flush()
        error_producer.close()


cli.add_command(consume)
cli.add_command(init_config)


if __name__ == "__main__":
    cli()
