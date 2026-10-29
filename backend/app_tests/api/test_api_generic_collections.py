import pytest
from rest_framework.test import APIClient

from core.models import AppliedControl, Evidence, Policy
from core.utils import RoleCodename
from iam.models import Folder, Role, RoleAssignment, User
from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType

from pmbok.models import CollectionItem, GenericCollection

URL = "/api/pmbok/generic-collections/"


@pytest.fixture
def setup(db):
    root = Folder.get_root_folder()
    domain = Folder.objects.create(
        parent_folder=root, name="Own", content_type=Folder.ContentType.DOMAIN
    )
    other_domain = Folder.objects.create(
        parent_folder=root, name="Other", content_type=Folder.ContentType.DOMAIN
    )
    admin = User.objects.create_superuser("collections-admin@tests.com")
    admin_client = APIClient()
    admin_client.force_authenticate(admin)

    analyst = User.objects.create_user("collections-analyst@tests.com")
    assignment = RoleAssignment.objects.create(
        user=analyst,
        role=Role.objects.get(name=RoleCodename.ANALYST.value),
        folder=root,
        is_recursive=True,
    )
    assignment.perimeter_folders.add(domain)
    analyst_client = APIClient()
    analyst_client.force_authenticate(analyst)

    return {
        "domain": domain,
        "other_domain": other_domain,
        "admin": admin_client,
        "analyst": analyst_client,
        "collection": GenericCollection.objects.create(name="Project", folder=domain),
        "other_collection": GenericCollection.objects.create(
            name="Hidden", folder=other_domain
        ),
    }


def ids(entries):
    return {entry["id"] for entry in entries}


@pytest.mark.django_db
class TestGenericCollectionItems:
    def test_items_round_trip_and_policies_stay_apart(self, setup):
        domain, collection = setup["domain"], setup["collection"]
        control = AppliedControl.objects.create(name="MFA", folder=domain)
        policy = Policy.objects.create(name="Access policy", folder=domain)
        evidence = Evidence.objects.create(name="Report", folder=domain)

        res = setup["admin"].patch(
            f"{URL}{collection.id}/",
            {
                "applied_controls": [str(control.id)],
                "policies": [str(policy.id)],
                "documents": [str(evidence.id)],
            },
            format="json",
        )
        assert res.status_code == 200, res.json()

        data = setup["admin"].get(f"{URL}{collection.id}/").json()
        assert ids(data["applied_controls"]) == {str(control.id)}
        assert ids(data["policies"]) == {str(policy.id)}
        assert ids(data["documents"]) == {str(evidence.id)}

        res = setup["admin"].patch(
            f"{URL}{collection.id}/", {"applied_controls": []}, format="json"
        )
        assert res.status_code == 200, res.json()
        assert list(collection.get_items("policies")) == [policy]
        assert not collection.get_items("applied_controls").exists()

    def test_object_lists_filter_by_collection(self, setup):
        domain, collection = setup["domain"], setup["collection"]
        inside = Evidence.objects.create(name="Inside", folder=domain)
        Evidence.objects.create(name="Outside", folder=domain)
        collection.set_items("documents", [inside])

        res = setup["admin"].get(f"/api/evidences/?genericcollection={collection.id}")
        assert res.status_code == 200
        assert ids(res.json()["results"]) == {str(inside.id)}

    def test_write_payload_lists_only_visible_items(self, setup):
        collection = setup["collection"]
        own = Evidence.objects.create(name="Own", folder=setup["domain"])
        hidden = Evidence.objects.create(name="Hidden", folder=setup["other_domain"])
        collection.set_items("documents", [own, hidden])

        data = setup["analyst"].get(f"{URL}{collection.id}/object/").json()
        assert data["documents"] == [str(own.id)]

    def test_applied_controls_tab_and_picker_leave_policies_out(self, setup):
        domain, collection = setup["domain"], setup["collection"]
        control = AppliedControl.objects.create(name="MFA", folder=domain)
        policy = Policy.objects.create(name="Access policy", folder=domain)
        collection.set_items("applied_controls", [control])
        collection.set_items("policies", [policy])

        res = setup["admin"].get(
            f"/api/applied-controls/?genericcollection={collection.id}"
        )
        assert ids(res.json()["results"]) == {str(control.id)}
        res = setup["admin"].get(f"/api/policies/?genericcollection={collection.id}")
        assert ids(res.json()["results"]) == {str(policy.id)}
        res = setup["admin"].get("/api/applied-controls/?exclude_category=policy")
        assert str(policy.id) not in ids(res.json()["results"])
        assert str(control.id) in ids(res.json()["results"])

    def test_filter_ignores_unregistered_models_and_unknown_ids(self, setup):
        Evidence.objects.create(name="Report", folder=setup["domain"])
        res = setup["admin"].get(
            f"/api/folders/?genericcollection={setup['collection'].id}"
        )
        assert res.status_code == 200
        assert res.json()["results"] == []
        res = setup["admin"].get(
            "/api/evidences/?genericcollection=00000000-0000-0000-0000-000000000000"
        )
        assert res.status_code == 200
        assert res.json()["results"] == []

    def test_adding_an_item_is_audited(self, setup):
        evidence = Evidence.objects.create(name="Report", folder=setup["domain"])
        setup["collection"].set_items("documents", [evidence])
        assert LogEntry.objects.filter(
            content_type=ContentType.objects.get_for_model(CollectionItem),
            action=LogEntry.Action.CREATE,
        ).exists()
        assert Folder.get_folder(setup["collection"].items.get()) == setup["domain"]

    def test_deleting_an_object_drops_its_items(self, setup):
        evidence = Evidence.objects.create(name="Gone", folder=setup["domain"])
        setup["collection"].set_items("documents", [evidence])
        Evidence.objects.filter(pk=evidence.pk).delete()
        assert not CollectionItem.objects.filter(object_id=evidence.pk).exists()

    def test_hidden_items_are_not_shown_and_survive_an_edit(self, setup):
        collection = setup["collection"]
        hidden = Evidence.objects.create(name="Hidden", folder=setup["other_domain"])
        own = Evidence.objects.create(name="Own", folder=setup["domain"])
        collection.set_items("documents", [hidden])

        data = setup["analyst"].get(f"{URL}{collection.id}/").json()
        assert data["documents"] == []

        res = setup["analyst"].patch(
            f"{URL}{collection.id}/", {"documents": [str(own.id)]}, format="json"
        )
        assert res.status_code == 200, res.json()
        assert set(collection.get_items("documents")) == {hidden, own}

    def test_linking_a_hidden_item_is_refused(self, setup):
        hidden = Evidence.objects.create(name="Hidden", folder=setup["other_domain"])
        res = setup["analyst"].patch(
            f"{URL}{setup['collection'].id}/",
            {"documents": [str(hidden.id)]},
            format="json",
        )
        assert res.status_code == 403
        assert not setup["collection"].items.exists()


@pytest.mark.django_db
class TestCollectionMembershipFromTheObject:
    def test_joining_a_changeable_collection(self, setup):
        evidence = Evidence.objects.create(name="Report", folder=setup["domain"])
        res = setup["analyst"].patch(
            f"/api/evidences/{evidence.id}/",
            {"genericcollection": [str(setup["collection"].id)]},
            format="json",
        )
        assert res.status_code == 200, res.json()
        assert list(GenericCollection.containing(evidence)) == [setup["collection"]]

    def test_joining_a_hidden_collection_is_refused(self, setup):
        evidence = Evidence.objects.create(name="Report", folder=setup["domain"])
        res = setup["analyst"].patch(
            f"/api/evidences/{evidence.id}/",
            {"genericcollection": [str(setup["other_collection"].id)]},
            format="json",
        )
        assert res.status_code == 403
        assert not GenericCollection.containing(evidence).exists()

    def test_hidden_memberships_survive_an_edit(self, setup):
        evidence = Evidence.objects.create(name="Report", folder=setup["domain"])
        setup["other_collection"].set_items("documents", [evidence])
        res = setup["analyst"].patch(
            f"/api/evidences/{evidence.id}/",
            {"genericcollection": [str(setup["collection"].id)]},
            format="json",
        )
        assert res.status_code == 200, res.json()
        assert set(GenericCollection.containing(evidence)) == {
            setup["collection"],
            setup["other_collection"],
        }

    def test_hidden_collections_do_not_filter_object_lists(self, setup):
        evidence = Evidence.objects.create(name="Report", folder=setup["domain"])
        setup["other_collection"].set_items("documents", [evidence])
        res = setup["analyst"].get(
            f"/api/evidences/?genericcollection={setup['other_collection'].id}"
        )
        assert res.status_code == 200
        assert res.json()["results"] == []
