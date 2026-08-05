import pytest
from django.urls import reverse
from rest_framework import status

from core.models import AssetClass


@pytest.fixture
def user_classes():
    """A → B → C chain of user-created (non built-in) classes."""
    a = AssetClass.objects.create(name="ZZTestA")
    b = AssetClass.objects.create(name="ZZTestB", parent=a)
    c = AssetClass.objects.create(name="ZZTestC", parent=b)
    return a, b, c


@pytest.mark.django_db
class TestAssetClassBuiltins:
    """Seeded CIS classes are re-created at every startup: hidable, not deletable."""

    def test_seeded_classes_are_builtin(self):
        assert AssetClass.objects.exists(), "startup should seed the CIS taxonomy"
        assert not AssetClass.objects.filter(builtin=False).exists()

    def test_builtin_class_visibility_editable_but_not_name(self, authenticated_client):
        cls = AssetClass.objects.filter(builtin=True).first()
        original_name = cls.name

        url = reverse("asset-class-detail", args=[cls.id])
        response = authenticated_client.patch(
            url, {"is_visible": False, "name": "hacked"}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        cls.refresh_from_db()
        assert cls.is_visible is False
        assert cls.name == original_name

    def test_builtin_class_cannot_be_deleted(self, authenticated_client):
        cls = AssetClass.objects.filter(builtin=True).first()

        url = reverse("asset-class-detail", args=[cls.id])
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert AssetClass.objects.filter(id=cls.id).exists()

    def test_user_class_under_builtin_parent_is_not_builtin(self, authenticated_client):
        parent = AssetClass.objects.filter(builtin=True).first()

        response = authenticated_client.post(
            reverse("asset-class-list"),
            {"name": "Custom subclass", "parent": str(parent.id)},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        created = AssetClass.objects.get(id=response.json()["id"])
        assert created.builtin is False
        assert created.parent == parent

    def test_builtin_flag_cannot_be_set_through_the_api(self, authenticated_client):
        response = authenticated_client.post(
            reverse("asset-class-list"),
            {"name": "Pretending to be builtin", "builtin": True},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert AssetClass.objects.get(id=response.json()["id"]).builtin is False


@pytest.mark.django_db
class TestAssetClassCycles:
    """full_path walks the parent chain, so a cycle turns every read into a 500."""

    def test_self_parent_is_rejected(self, authenticated_client, user_classes):
        a, _, _ = user_classes

        response = authenticated_client.patch(
            reverse("asset-class-detail", args=[a.id]),
            {"parent": str(a.id)},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        a.refresh_from_db()
        assert a.parent is None

    def test_descendant_as_parent_is_rejected(self, authenticated_client, user_classes):
        a, _, c = user_classes

        response = authenticated_client.patch(
            reverse("asset-class-detail", args=[a.id]),
            {"parent": str(c.id)},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        a.refresh_from_db()
        assert a.parent is None

    def test_legitimate_reparent_is_accepted(self, authenticated_client, user_classes):
        a, _, c = user_classes

        response = authenticated_client.patch(
            reverse("asset-class-detail", args=[c.id]),
            {"parent": str(a.id)},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        c.refresh_from_db()
        assert c.parent == a


@pytest.mark.django_db
class TestAssetClassTree:
    def test_tree_nodes_carry_id_and_flags(self, authenticated_client):
        response = authenticated_client.get(reverse("asset-class-tree"))

        assert response.status_code == status.HTTP_200_OK
        roots = response.json()
        assert roots, "tree should not be empty"
        assert {"id", "name", "builtin", "is_visible", "children"} <= set(roots[0])

    def test_hidden_leaf_is_pruned_from_the_visible_tree(
        self, authenticated_client, user_classes
    ):
        a, b, c = user_classes
        c.is_visible = False
        c.save()

        response = authenticated_client.get(
            reverse("asset-class-tree"), {"visible_only": "true"}
        )

        names = set()

        def collect(nodes):
            for node in nodes:
                names.add(node["name"])
                collect(node["children"])

        collect(response.json())
        assert "ZZTestC" not in names
        assert "ZZTestB" in names

    def test_hidden_node_with_visible_child_is_kept_unselectable(
        self, authenticated_client, user_classes
    ):
        a, b, c = user_classes
        b.is_visible = False
        b.save()

        response = authenticated_client.get(
            reverse("asset-class-tree"), {"visible_only": "true"}
        )

        def find(nodes, name):
            for node in nodes:
                if node["name"] == name:
                    return node
                found = find(node["children"], name)
                if found:
                    return found
            return None

        node = find(response.json(), "ZZTestB")
        assert node is not None, "hidden node must survive to carry its visible child"
        assert node["is_visible"] is False
        assert [child["name"] for child in node["children"]] == ["ZZTestC"]

    def test_full_tree_keeps_hidden_classes(self, authenticated_client, user_classes):
        a, b, c = user_classes
        c.is_visible = False
        c.save()

        response = authenticated_client.get(reverse("asset-class-tree"))

        names = set()

        def collect(nodes):
            for node in nodes:
                names.add(node["name"])
                collect(node["children"])

        collect(response.json())
        assert "ZZTestC" in names


@pytest.mark.django_db
class TestAssetClassNestedCreate:
    """The children table creates a class with `parent` prefilled."""

    def test_read_serializer_exposes_folder(self, authenticated_client):
        """Folder-scoped permission checks need the folder in the payload."""
        cls = AssetClass.objects.filter(builtin=True).first()

        body = authenticated_client.get(
            reverse("asset-class-detail", args=[cls.id])
        ).json()

        assert body.get("folder", {}).get("id")

    def test_children_are_listed_by_parent_filter(
        self, authenticated_client, user_classes
    ):
        """The children table fetches /asset-class?parent=<id>."""
        a, b, _ = user_classes

        response = authenticated_client.get(
            reverse("asset-class-list"), {"parent": str(a.id)}
        )

        assert [row["name"] for row in response.json()["results"]] == [b.name]

    def test_child_lands_in_the_same_folder_as_its_parent(self, authenticated_client):
        parent = AssetClass.objects.filter(builtin=True).first()

        response = authenticated_client.post(
            reverse("asset-class-list"),
            {"name": "Custom child of a builtin", "parent": str(parent.id)},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        child = AssetClass.objects.get(id=response.json()["id"])
        assert child.parent == parent
        assert child.folder_id == parent.folder_id
        assert child.builtin is False


@pytest.mark.django_db
class TestAssetClassTranslations:
    """Custom names are free text, so they carry per-object translations."""

    @pytest.fixture
    def translated_class(self):
        return AssetClass.objects.create(
            name="Industrial controllers",
            description="PLCs and SCADA equipment",
            translations={
                "fr": {
                    "name": "Automates industriels",
                    "description": "Automates et équipements SCADA",
                }
            },
        )

    def test_translated_name_follows_accept_language(
        self, authenticated_client, translated_class
    ):
        url = reverse("asset-class-detail", args=[translated_class.id])

        fr = authenticated_client.get(url, headers={"accept-language": "fr"}).json()
        assert fr["translated_name"] == "Automates industriels"
        assert fr["translated_description"] == "Automates et équipements SCADA"
        # Canonical fields stay untranslated so the edit form round-trips.
        assert fr["name"] == "Industrial controllers"

        en = authenticated_client.get(url, headers={"accept-language": "en"}).json()
        assert en["translated_name"] == "Industrial controllers"

    def test_missing_locale_falls_back_to_name(
        self, authenticated_client, translated_class
    ):
        response = authenticated_client.get(
            reverse("asset-class-detail", args=[translated_class.id]),
            headers={"accept-language": "de"},
        )
        assert response.json()["translated_name"] == "Industrial controllers"

    def test_builtin_falls_back_to_its_i18n_key(self, authenticated_client):
        """The raw name is the key the frontend resolves; it must survive."""
        cls = AssetClass.objects.get(name="assetClassDevices", parent=None)

        response = authenticated_client.get(
            reverse("asset-class-detail", args=[cls.id]),
            headers={"accept-language": "fr"},
        )
        assert response.json()["translated_name"] == "assetClassDevices"

    def test_tree_nodes_carry_translated_name(
        self, authenticated_client, translated_class
    ):
        """The tree action bypasses the serializer."""
        response = authenticated_client.get(
            reverse("asset-class-tree"), headers={"accept-language": "fr"}
        )

        def find(nodes, name):
            for node in nodes:
                if node["name"] == name:
                    return node
                found = find(node["children"], name)
                if found:
                    return found
            return None

        node = find(response.json(), "Industrial controllers")
        assert node is not None
        assert node["translated_name"] == "Automates industriels"

    def test_translations_are_writable(self, authenticated_client, translated_class):
        response = authenticated_client.patch(
            reverse("asset-class-detail", args=[translated_class.id]),
            {"translations": {"fr": {"name": "Automates"}}},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        translated_class.refresh_from_db()
        assert translated_class.translations["fr"]["name"] == "Automates"

    def test_builtin_translations_are_not_writable(self, authenticated_client):
        """Built-in labels live in messages/*.json."""
        cls = AssetClass.objects.filter(builtin=True).first()

        response = authenticated_client.patch(
            reverse("asset-class-detail", args=[cls.id]),
            {"translations": {"fr": {"name": "Piraté"}}},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        cls.refresh_from_db()
        assert not (cls.translations or {})


@pytest.mark.django_db
class TestAssetClassCascadePreview:
    """`parent` is CASCADE: deleting a class takes its whole subtree."""

    def test_whole_subtree_is_previewed_as_deleted(
        self, authenticated_client, user_classes
    ):
        a, b, c = user_classes

        response = authenticated_client.get(
            reverse("asset-class-cascade-info", args=[a.id])
        )

        assert response.status_code == status.HTTP_200_OK
        deleted = {o["name"] for o in response.json()["deleted"]["related_objects"]}
        assert {b.name, c.name} <= deleted

    def test_nothing_blocks_an_asset_class_deletion(
        self, authenticated_client, user_classes
    ):
        """The `blocked` bucket exists for other models; not this one."""
        a, _, _ = user_classes

        response = authenticated_client.get(
            reverse("asset-class-cascade-info", args=[a.id])
        )

        assert response.json()["blocked"]["count"] == 0

    def test_linked_assets_are_affected_not_deleted(
        self, authenticated_client, user_classes
    ):
        """Asset.asset_class is SET_NULL: assets are unclassified, not deleted."""
        from core.models import Asset

        _, _, c = user_classes
        Asset.objects.create(name="ZZTestAsset", asset_class=c)

        body = authenticated_client.get(
            reverse("asset-class-cascade-info", args=[c.id])
        ).json()

        assert "ZZTestAsset" in [o["name"] for o in body["affected"]["related_objects"]]
        assert "ZZTestAsset" not in [
            o["name"] for o in body["deleted"]["related_objects"]
        ]


@pytest.mark.django_db
class TestAssetClassDeletion:
    def test_deleting_a_class_cascades_to_its_whole_subtree(
        self, authenticated_client, user_classes
    ):
        a, b, c = user_classes

        response = authenticated_client.delete(
            reverse("asset-class-detail", args=[a.id])
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not AssetClass.objects.filter(id__in=[a.id, b.id, c.id]).exists()

    def test_cascade_unclassifies_assets_but_never_deletes_them(
        self, authenticated_client, user_classes
    ):
        from core.models import Asset

        a, _, c = user_classes
        asset = Asset.objects.create(name="ZZTestAsset", asset_class=c)

        authenticated_client.delete(reverse("asset-class-detail", args=[a.id]))

        asset.refresh_from_db()
        assert asset.asset_class is None

    def test_deleting_a_leaf_class_succeeds(self, authenticated_client, user_classes):
        _, _, c = user_classes

        response = authenticated_client.delete(
            reverse("asset-class-detail", args=[c.id])
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not AssetClass.objects.filter(id=c.id).exists()
