import pytest
from rest_framework import status

# List endpoints whose model has neither ``name`` nor ``description`` and whose
# viewset inherits ``BaseModelViewSet``'s default search fields. Before the
# effective search fields were resolved against the model, ``?search=`` on any of
# them raised ``FieldError`` and returned a 500.
ENDPOINTS_WITHOUT_NAME_DESCRIPTION = [
    "/api/evidence-revisions/",
    "/api/requirement-assignments/",
    "/api/document-revisions/",
    # /api/document-attachments/ also lacks name/description but its list
    # endpoint has no read serializer yet, so it fails for unrelated reasons.
    "/api/ebios-rm/ro-to/",
    "/api/ebios-rm/stakeholders/",
    "/api/ebios-rm/operational-scenarios/",
    "/api/ebios-rm/kill-chains/",
    "/api/pmbok/responsibility-assignments/",
    "/api/pmbok/responsibility-matrix-actors/",
    "/api/resilience/escalation-thresholds/",
    "/api/integrations/configs/",
]


@pytest.mark.django_db
@pytest.mark.parametrize("url", ENDPOINTS_WITHOUT_NAME_DESCRIPTION)
def test_search_param_does_not_error_on_models_without_default_fields(
    authenticated_client, url
):
    response = authenticated_client.get(url, {"search": "foo"})
    assert response.status_code == status.HTTP_200_OK, response.content
