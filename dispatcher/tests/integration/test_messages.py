import uuid
from testcontainers.core.container import DockerContainer
from testcontainers.core.image import DockerImage
from testcontainers.core.waiting_utils import wait_for_logs
from testcontainers.kafka import KafkaContainer
from pathlib import Path
from click.testing import CliRunner

import pytest

import dispatcher as ds

BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = BASE_DIR.parent / "backend"

DJANGO_SUPERUSER_EMAIL = "admin@tests.com"
DJANGO_SUPERUSER_PASSWORD = "badpass12345"


@pytest.fixture(scope="session")
def kafka():
    with KafkaContainer() as kafka:
        connection = kafka.get_bootstrap_server()
        print(f"Kafka running at {connection}")
        yield kafka


@pytest.fixture(scope="session")
def api():
    with DockerImage(path=BACKEND_DIR) as image:
        with (
            DockerContainer(image=str(image))
            .with_env("ALLOWED_HOSTS", "backend,localhost")
            .with_env("DJANGO_DEBUG", "True")
            .with_env("DJANGO_SUPERUSER_EMAIL", DJANGO_SUPERUSER_EMAIL)
            .with_env("DJANGO_SUPERUSER_PASSWORD", DJANGO_SUPERUSER_PASSWORD)
            .with_volume_mapping(
                str(BACKEND_DIR / "db"),
                "/code/db",
                "rw",
            )
            .with_exposed_ports(8000) as container
        ):
            wait_for_logs(container, "Booting worker with pid")
            yield container


@pytest.fixture(scope="session")
def cli():
    """Fixture to provide a CLI runner for testing."""
    return CliRunner(mix_stderr=False)


def test_api_is_running(api: DockerContainer):
    logs = api.get_logs().decode()
    assert "No migrations to apply" in logs
    assert api.get_exposed_port(8000)

def test_kafka_is_running(kafka: KafkaContainer):
    assert kafka.get_bootstrap_server() is not None
    assert kafka.get_exposed_port(9093), (
        f"Kafka is not running on port 9093, but on {kafka.ports}"
    )


def test_dispatcher_is_running(
    cli: CliRunner,
):
    result = cli.invoke(ds.cli, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output


def test_dispatcher_can_authenticate_using_credentials(
    cli: CliRunner, api: DockerContainer
):
    result = cli.invoke(
        ds.cli,
        [
            "auth",
            "--email",
            DJANGO_SUPERUSER_EMAIL,
            "--password",
            DJANGO_SUPERUSER_PASSWORD,
        ],
    )
    assert result.exit_code == 0
    print(vars(result))
    assert "Successfully authenticated" in result.output
