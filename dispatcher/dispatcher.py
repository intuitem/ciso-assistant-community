import json
import os
import sys

import click
import requests
import yaml
from kafka import KafkaConsumer
from kafka.errors import UnsupportedCodecError
from rich import print as rprint

from messages import message_registry
from settings import API_URL, VERIFY_CERTIFICATE, EMAIL, PASSWORD

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
        print("trying credentials from the config file", file=sys.stderr)
        if EMAIL and PASSWORD:
            data = {"username": EMAIL, "password": PASSWORD}
        else:
            print("Could not find any usable credentials.", file=sys.stderr)
            sys.exit(1)
    headers = {"accept": "application/json", "Content-Type": "application/json"}

    res = requests.post(url, data, headers, verify=VERIFY_CERTIFICATE)
    print(res.status_code)
    if res.status_code == 200:
        with open(".tmp.yaml", "w") as yfile:
            yaml.safe_dump(res.json(), yfile)
            print("Looks good, you can move to other commands.", file=sys.stderr)
    else:
        print(
            "Check your credentials again. You can set them on the config file or on the command line.",
            file=sys.stderr,
        )
        print(res.json())


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

    try:
        rprint("Starting consumer")
        for msg in consumer:
            rprint(f"Consumed record. key={msg.key}, value={msg.value}")
            try:
                message = json.loads(msg.value.decode("utf-8"))
            except Exception as e:
                rprint(f"Error decoding message: {e}")
            else:
                if message.get("event_type") not in message_registry.REGISTRY:
                    rprint(
                        "Event type not supported. Skipping. Check the event_registry for supported events."
                    )
                    continue
                rprint(f"Processing event: {message.get('event_type')}")
                message_registry.REGISTRY[message.get("event_type")](message)

    except UnsupportedCodecError as e:
        rprint("KO", e)


cli.add_command(auth)
cli.add_command(consume)


if __name__ == "__main__":
    cli()
