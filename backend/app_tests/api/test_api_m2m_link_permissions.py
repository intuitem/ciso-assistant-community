"""A many-to-many link has no owner side: whichever model declares the field,
editing it needs change on the edited object, view on each object linked and
nothing on an object unlinked."""

import uuid

import pytest
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APIClient

from core.models import AppliedControl, Evidence
from core.utils import RoleCodename
from iam.models import Folder, Role, RoleAssignment, User

# (endpoint, model, field) of the edited end, then the model at the other end.
# AppliedControl declares `evidences`; Evidence writes it through the reverse accessor.
DIRECTIONS = {
    "declared": ("applied-controls", AppliedControl, "evidences", Evidence),
    "reverse": ("evidences", Evidence, "applied_controls", AppliedControl),
}


def _domain(label):
    return Folder.objects.create(
        name=f"m2m-{label}-{uuid.uuid4().hex[:6]}",
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


def _client(grants):
    user = User.objects.create_user(f"m2m-{uuid.uuid4().hex[:6]}@test.com")
    for folder, role in grants:
        RoleAssignment.objects.create(
            user=user,
            role=Role.objects.get(name=role.value),
            folder=Folder.get_root_folder(),
            is_recursive=True,
        ).perimeter_folders.add(folder)
    client = APIClient()
    _, token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


@pytest.mark.django_db
@pytest.mark.parametrize("direction", DIRECTIONS)
class TestM2MLinkPermissions:
    def setup_method(self):
        self.mine, self.readable, self.hidden = (
            _domain("mine"),
            _domain("readable"),
            _domain("hidden"),
        )
        self.client = _client(
            [(self.mine, RoleCodename.ANALYST), (self.readable, RoleCodename.READER)]
        )

    def _objects(self, direction, edited_folder, other_folder):
        endpoint, model, field, other_model = DIRECTIONS[direction]
        edited = model.objects.create(name="edited", folder=edited_folder)
        other = other_model.objects.create(name="other", folder=other_folder)
        return f"/api/{endpoint}/{edited.id}/", edited, field, other

    def test_view_on_the_other_end_is_enough_to_link(self, direction):
        url, edited, field, other = self._objects(direction, self.mine, self.readable)
        r = self.client.patch(url, {field: [str(other.id)]}, format="json")
        assert r.status_code == status.HTTP_200_OK, r.content
        assert list(getattr(edited, field).all()) == [other]

    def test_invisible_other_end_cannot_be_linked(self, direction):
        url, edited, field, other = self._objects(direction, self.mine, self.hidden)
        r = self.client.patch(url, {field: [str(other.id)]}, format="json")
        assert r.status_code == status.HTTP_403_FORBIDDEN, r.content
        assert not getattr(edited, field).exists()

    def test_invisible_other_end_can_be_unlinked(self, direction):
        url, edited, field, other = self._objects(direction, self.mine, self.hidden)
        getattr(edited, field).add(other)
        r = self.client.patch(url, {field: []}, format="json")
        assert r.status_code == status.HTTP_200_OK, r.content
        assert not getattr(edited, field).exists()

    def test_echoed_hidden_link_is_kept(self, direction):
        # The edit form sends hidden links back untouched; that is not linking them.
        url, edited, field, other = self._objects(direction, self.mine, self.hidden)
        getattr(edited, field).add(other)
        r = self.client.patch(url, {field: [str(other.id)]}, format="json")
        assert r.status_code == status.HTTP_200_OK, r.content
        assert list(getattr(edited, field).all()) == [other]

    def test_view_only_end_cannot_be_edited(self, direction):
        url, edited, field, other = self._objects(direction, self.readable, self.mine)
        getattr(edited, field).add(other)
        r = self.client.patch(url, {field: []}, format="json")
        assert r.status_code == status.HTTP_403_FORBIDDEN, r.content
        assert list(getattr(edited, field).all()) == [other]
