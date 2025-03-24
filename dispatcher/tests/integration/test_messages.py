from time import sleep
import uuid
from testcontainers.core.container import DockerContainer
from testcontainers.core.image import DockerImage
from testcontainers.core.waiting_utils import wait_for_logs
from testcontainers.kafka import RedpandaContainer
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = BASE_DIR.parent / "backend"


@pytest.fixture(scope="session")
def redpanda():
    with RedpandaContainer() as redpanda:
        connection = redpanda.get_bootstrap_server()
        print(connection)
        yield redpanda


@pytest.fixture(scope="session")
def dispatcher():
    with DockerImage(path=BASE_DIR) as image:
        with DockerContainer(image=str(image)) as container:
            for i in range(20):
                sleep(1)
                logs = container.get_logs()
                print(logs)
            delay = wait_for_logs(container, "Starting consumer")
            print(delay)
            yield container


# @pytest.fixture(scope="session")
# def dispatcher():
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
        for i in range(10):
            sleep(1)
            logs = container.get_logs()
            print(logs[0].decode())
        delay = wait_for_logs(container, "Starting consumer")
        print(delay)
