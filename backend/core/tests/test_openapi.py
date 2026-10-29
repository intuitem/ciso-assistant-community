from ciso_assistant import openapi
from ciso_assistant.openapi import split_namespace_tags


def _schema(paths):
    return {
        "paths": {
            path: {"get": {"operationId": path, "tags": [path.split("/")[2]]}}
            for path in paths
        }
    }


def test_large_namespace_is_split_per_resource(monkeypatch):
    monkeypatch.setattr(openapi, "MAX_NAMESPACE_OPERATIONS", 2)
    schema = split_namespace_tags(
        _schema(
            [
                "/api/ebios-rm/studies/",
                "/api/ebios-rm/studies/{id}/",
                "/api/ebios-rm/feared-events/",
                "/api/assets/",
                "/api/assets/{id}/",
                "/api/assets/graph/",
            ]
        ),
        None,
        None,
        True,
    )

    tags = {path: item["get"]["tags"] for path, item in schema["paths"].items()}
    assert tags["/api/ebios-rm/studies/{id}/"] == ["ebios-rm/studies"]
    assert tags["/api/ebios-rm/feared-events/"] == ["ebios-rm/feared-events"]
    assert tags["/api/assets/graph/"] == ["assets"]
    assert schema["tags"] == [
        {"name": "assets", "x-page-title": "Assets"},
        {"name": "ebios-rm", "x-page-title": "EBIOS RM"},
        {
            "name": "ebios-rm/feared-events",
            "x-page-title": "Feared events",
            "x-parent": "ebios-rm",
        },
        {
            "name": "ebios-rm/studies",
            "x-page-title": "Studies",
            "x-parent": "ebios-rm",
        },
    ]


def test_small_namespace_is_kept_whole():
    schema = split_namespace_tags(
        _schema(["/api/crq/studies/", "/api/crq/scenarios/"]), None, None, True
    )

    assert {item["get"]["tags"][0] for item in schema["paths"].values()} == {"crq"}


class _BaseViewSet:
    def list(self):
        """Implementation note from a shared base class."""


class _ViewSet(_BaseViewSet):
    """Public description of the endpoint."""

    def retrieve(self):
        """Public description of this action."""


def _description(action):
    view = _ViewSet()
    view.action = action
    schema = openapi.AutoSchema()
    schema.view = view
    schema.method = "GET"
    return schema.get_description()


def test_description_ignores_inherited_docstrings():
    assert _description("retrieve") == "Public description of this action."
    assert _description("list") == "Public description of the endpoint."


def test_page_titles():
    assert openapi._title("crq") == "Cyber Risk Quantification"
    assert openapi._title("ebios-rm/feared-events") == "Feared events"
    assert openapi._title("get_audits_metrics") == "Audits metrics"
