import settings
import sys

from loguru import logger

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


def build_kafka_config(use_auth: bool = settings.KAFKA_USE_AUTH) -> dict:
    """
    Returns the dict of kwargs to pass to KafkaConsumer/Producer.
    If use_auth=True, it will include the SASL/SSL or OAuthBearer settings.
    """
    if not settings.BOOTSTRAP_SERVERS:
        raise ValueError("BOOTSTRAP_SERVERS not configured")
    cfg = {
        "bootstrap_servers": settings.BOOTSTRAP_SERVERS,
    }

    if use_auth:
        logger.info(
            f"Configuring Kafka with authentication using mechanism: {settings.KAFKA_SASL_MECHANISM}"
        )

        if not settings.KAFKA_USERNAME or not settings.KAFKA_PASSWORD:
            raise ValueError(
                "KAFKA_USERNAME and KAFKA_PASSWORD must be provided when authentication is enabled"
            )

        if settings.KAFKA_SASL_MECHANISM.upper() in (
            "PLAIN",
            "SCRAM-SHA-256",
            "SCRAM-SHA-512",
        ):
            logger.debug(
                f"Using {settings.KAFKA_SASL_MECHANISM.upper()} authentication mechanism"
            )
            cfg.update(
                {
                    "security_protocol": "SASL_SSL",
                    "sasl_mechanism": settings.KAFKA_SASL_MECHANISM.upper(),
                    "sasl_plain_username": settings.KAFKA_USERNAME,
                    "sasl_plain_password": settings.KAFKA_PASSWORD,
                    # optional SSL cert files:
                    # "ssl_cafile": settings.KAFKA_SSL_CAFILE,
                    # "ssl_certfile": settings.KAFKA_SSL_CERTFILE,
                    # "ssl_keyfile": settings.KAFKA_SSL_KEYFILE,
                }
            )
        else:
            logger.error(f"Unsupported SASL mechanism: {settings.KAFKA_SASL_MECHANISM}")
            raise ValueError(
                f"Unsupported SASL mechanism: {settings.KAFKA_SASL_MECHANISM}"
            )

    return cfg
