"""An applied control can be linked to an existing document from its own side.

The relation is declared on the document (`DocumentContainer.applied_controls`,
related_name `control_documents`), so a ModelSerializer never exposes it on the
applied control. Without an explicit field the PATCH answers 200 and writes
nothing, which is what the Documents tab's attach button ran into.
"""

import pytest
from django.urls import reverse
from rest_framework import status as http

from core.models import AppliedControl
from core.tests.test_audit_word_export import (  # noqa: F401
    admin_client,
    app_config,
)
from doc_management.models import DocumentContainer
from iam.models import Folder


@pytest.fixture
def control_and_document(app_config):  # noqa: F811
    folder = Folder.objects.create(
        name="Control documents domain", content_type=Folder.ContentType.DOMAIN
    )
    control = AppliedControl.objects.create(name="Backup encryption", folder=folder)
    document = DocumentContainer.objects.create(name="Backup policy", folder=folder)
    return control, document


@pytest.mark.django_db
def test_document_can_be_linked_from_the_applied_control(
    admin_client,  # noqa: F811
    control_and_document,
):
    control, document = control_and_document
    response = admin_client.patch(
        reverse("applied-controls-detail", args=[control.id]),
        {"control_documents": [str(document.id)]},
        format="json",
    )
    assert response.status_code == http.HTTP_200_OK
    assert list(control.control_documents.all()) == [document]


@pytest.mark.django_db
def test_linking_one_document_does_not_drop_the_others(
    admin_client,  # noqa: F811
    control_and_document,
):
    """A silently dropped field also passes the test above when the link is
    seeded beforehand; sending a second document proves the write happened."""
    control, document = control_and_document
    other = DocumentContainer.objects.create(
        name="Restore procedure", folder=control.folder
    )
    control.control_documents.add(document)

    response = admin_client.patch(
        reverse("applied-controls-detail", args=[control.id]),
        {"control_documents": [str(document.id), str(other.id)]},
        format="json",
    )
    assert response.status_code == http.HTTP_200_OK
    assert control.control_documents.count() == 2
