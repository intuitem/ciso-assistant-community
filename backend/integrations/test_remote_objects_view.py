from unittest.mock import MagicMock, patch

from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from integrations.views import IntegrationConfigurationViewSet


def _call(query_string=""):
    factory = APIRequestFactory()
    request = Request(
        factory.get(f"/integrations/configs/x/remote-objects/?{query_string}")
    )
    view = IntegrationConfigurationViewSet()
    view.get_object = MagicMock()
    client = MagicMock()
    client.list_remote_objects.return_value = []
    with patch(
        "integrations.views.IntegrationRegistry.get_client", return_value=client
    ):
        response = view._list_remote_objects(request, pk="x")
    return response, client


def test_forwards_search_and_id_params():
    response, client = _call("search=CISO-40&id=CISO-7&limit=20")

    assert response.status_code == 200
    query_params = client.list_remote_objects.call_args[1]["query_params"]
    assert query_params == {"search": "CISO-40", "id": "CISO-7", "limit": 20}


def test_limit_is_clamped_and_defaulted():
    _, client = _call("limit=5000")
    assert client.list_remote_objects.call_args[1]["query_params"]["limit"] == 100

    _, client = _call("limit=0")
    assert client.list_remote_objects.call_args[1]["query_params"]["limit"] == 1

    _, client = _call("limit=abc")
    assert client.list_remote_objects.call_args[1]["query_params"]["limit"] == 50

    _, client = _call()
    assert client.list_remote_objects.call_args[1]["query_params"]["limit"] == 50


def test_unknown_model_key_is_rejected():
    response, client = _call("model_key=nonsense")

    assert response.status_code == 400
    client.list_remote_objects.assert_not_called()
