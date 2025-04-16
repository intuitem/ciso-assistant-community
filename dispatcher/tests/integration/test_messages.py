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


@pytest.fixture(scope="session")
def kafka():
    with KafkaContainer() as kafka:
        connection = kafka.get_bootstrap_server()
        print(f"Kafka running at {connection}")
        yield kafka


@pytest.fixture(scope="session")
def api():
    with DockerImage(path=BACKEND_DIR) as image:
        DJANGO_SUPERUSER_PASSWORD = str(uuid.uuid4())
        with (
            DockerContainer(image=str(image))
            .with_env("ALLOWED_HOSTS", "backend,localhost")
            .with_env("DJANGO_DEBUG", "True")
            .with_env("DJANGO_SUPERUSER_EMAIL", "admin@tests.com")
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
def dispatcher():
    """Fixture to provide a CLI runner for testing."""
    return CliRunner(mix_stderr=False)


def test_api_is_running(api: DockerContainer):
    # assert api.get_exposed_port(8000) == 8000
    assert "No migrations to apply" in api.get_logs()[0].decode()
    assert api.get_exposed_port(8000)


def test_kafka_is_running(kafka: KafkaContainer):
    assert kafka.get_bootstrap_server() is not None
    assert kafka.get_exposed_port(9092), (
        f"Kafka is not running on port 9092, but on {kafka.ports}"
    )


def test_dispatcher_is_running(
    dispatcher: CliRunner,
):
    result = dispatcher.invoke(ds.auth, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output
