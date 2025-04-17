from dispatcher import settings


def build_kafka_config(use_auth: bool = settings.KAFKA_USE_AUTH) -> dict:
    """
    Returns the dict of kwargs to pass to KafkaConsumer/Producer.
    If use_auth=True, it will include the SASL/SSL or OAuthBearer settings.
    """
    cfg = {
        "bootstrap_servers": settings.BOOTSTRAP_SERVERS,
    }

    if use_auth:
        if settings.KAFKA_SASL_MECHANISM.upper() == "PLAIN":
            cfg.update(
                {
                    "security_protocol": "SASL_SSL",
                    "sasl_mechanism": "PLAIN",
                    "sasl_plain_username": settings.KAFKA_USERNAME,
                    "sasl_plain_password": settings.KAFKA_PASSWORD,
                    # optional SSL cert files:
                    # "ssl_cafile": settings.KAFKA_SSL_CAFILE,
                    # "ssl_certfile": settings.KAFKA_SSL_CERTFILE,
                    # "ssl_keyfile": settings.KAFKA_SSL_KEYFILE,
                }
            )
        else:
            raise ValueError(
                f"Unsupported SASL mechanism: {settings.KAFKA_SASL_MECHANISM}"
            )

    return cfg
