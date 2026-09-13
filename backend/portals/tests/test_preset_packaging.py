"""Round trip of a portal design through a library preset."""

import pytest
import yaml
from core.models import Framework, LoadedLibrary, QuickForm
from iam.models import Folder
from library.utils import PortalPresetImporter

from portals.models import Portal, PortalPreset
from portals.presets import build_preset_library
from portals.references import dereference, resolve


@pytest.fixture
def catalog(db):
    folder = Folder.get_root_folder()
    library = LoadedLibrary.objects.create(
        name="Catalog",
        urn="urn:test:portals:lib",
        ref_id="CAT",
        version=1,
        locale="en",
        default_locale=True,
        folder=folder,
    )
    framework = Framework.objects.create(
        name="ISO-ish",
        urn="urn:test:portals:fw",
        folder=folder,
        library=library,
        locale="en",
        default_locale=True,
    )
    quick_form = QuickForm.objects.create(
        name="Access request",
        urn="urn:test:portals:qf",
        ref_id="QF",
        folder=folder,
        library=library,
        locale="en",
        default_locale=True,
    )
    return {"folder": folder, "library": library, "fw": framework, "qf": quick_form}


def _portal(catalog, items):
    return Portal.objects.create(
        name="Onboarding",
        folder=catalog["folder"],
        content={"sections": [{"title": "Start here", "items": items}]},
    )


@pytest.mark.django_db
class TestDereference:
    def test_local_ids_become_urns(self, catalog):
        portal = _portal(
            catalog,
            [
                {
                    "id": "t1",
                    "kind": "assessment",
                    "title": "Run the audit",
                    "target": {
                        "framework": str(catalog["fw"].id),
                        "implementation_groups": ["IG1"],
                        "folder": str(catalog["folder"].id),
                    },
                }
            ],
        )
        content, unwired = dereference(portal.content)
        target = content["sections"][0]["items"][0]["target"]

        assert unwired == []
        assert target["framework_urn"] == "urn:test:portals:fw"
        assert "framework" not in target
        assert target["implementation_groups"] == ["IG1"]
        assert "folder" not in target

    def test_source_portal_is_untouched(self, catalog):
        portal = _portal(
            catalog,
            [
                {
                    "id": "t1",
                    "kind": "assessment",
                    "target": {"framework": str(catalog["fw"].id)},
                }
            ],
        )
        dereference(portal.content)
        portal.refresh_from_db()

        assert portal.content["sections"][0]["items"][0]["target"] == {
            "framework": str(catalog["fw"].id)
        }

    def test_quick_form_travels_without_its_publication(self, catalog):
        portal = _portal(
            catalog,
            [
                {
                    "id": "t1",
                    "kind": "quickForm",
                    "target": {
                        "quick_form": str(catalog["qf"].id),
                        "publication": "a-local-publication-id",
                        "reviewers": ["an-actor-id"],
                    },
                }
            ],
        )
        content, unwired = dereference(portal.content)
        target = content["sections"][0]["items"][0]["target"]

        assert unwired == []
        assert target == {"quick_form_urn": "urn:test:portals:qf"}

    @pytest.mark.parametrize(
        "item,dropped",
        [
            (
                {"kind": "framework", "title": "Posture", "target": {"snapshot": "x"}},
                "snapshot",
            ),
            (
                {
                    "kind": "certificationDocument",
                    "title": "SOC 2",
                    "target": {"dest": "document", "token": "x"},
                },
                "token",
            ),
        ],
    )
    def test_instance_bound_tiles_travel_unwired(self, catalog, item, dropped):
        portal = _portal(catalog, [item])
        content, unwired = dereference(portal.content)
        target = content["sections"][0]["items"][0]["target"]

        assert len(unwired) == 1
        assert item["title"] in unwired[0]
        assert dropped not in target

    def test_link_shaped_certification_document_travels(self, catalog):
        portal = _portal(
            catalog,
            [
                {
                    "kind": "certificationDocument",
                    "target": {"dest": "link", "url": "https://example.test/soc2"},
                }
            ],
        )
        content, unwired = dereference(portal.content)

        assert unwired == []
        assert content["sections"][0]["items"][0]["target"]["url"] == (
            "https://example.test/soc2"
        )

    def test_a_framework_outside_any_library_has_no_urn_to_travel_under(self, catalog):
        local_only = Framework.objects.create(
            name="Homegrown", folder=catalog["folder"], locale="en", default_locale=True
        )
        portal = _portal(
            catalog,
            [
                {
                    "kind": "assessment",
                    "title": "Homegrown audit",
                    "target": {"framework": str(local_only.id)},
                }
            ],
        )
        _content, unwired = dereference(portal.content)

        assert len(unwired) == 1
        assert "no URN" in unwired[0]


@pytest.mark.django_db
class TestResolve:
    def test_urns_become_local_ids_and_are_kept(self, catalog):
        content, unwired = resolve(
            {
                "sections": [
                    {
                        "items": [
                            {
                                "kind": "assessment",
                                "target": {"framework_urn": "urn:test:portals:fw"},
                            }
                        ]
                    }
                ]
            }
        )
        target = content["sections"][0]["items"][0]["target"]

        assert unwired == []
        assert target["framework"] == str(catalog["fw"].id)
        assert target["framework_urn"] == "urn:test:portals:fw"

    def test_missing_reference_is_reported_not_silently_dropped(self, catalog):
        _content, unwired = resolve(
            {
                "sections": [
                    {
                        "items": [
                            {
                                "kind": "assessment",
                                "title": "Run the audit",
                                "target": {"framework_urn": "urn:test:absent:fw"},
                            }
                        ]
                    }
                ]
            }
        )

        assert len(unwired) == 1
        assert "not loaded" in unwired[0]


@pytest.mark.django_db
class TestRoundTrip:
    def test_export_then_load_rewires_every_tile(self, catalog):
        portal = _portal(
            catalog,
            [
                {
                    "id": "t1",
                    "kind": "assessment",
                    "title": "Run the audit",
                    "target": {"framework": str(catalog["fw"].id)},
                },
                {
                    "id": "t2",
                    "kind": "quickForm",
                    "title": "Ask for access",
                    "target": {"quick_form": str(catalog["qf"].id)},
                },
                {"id": "t3", "kind": "create", "target": {"model": "incidents"}},
            ],
        )

        document, unwired = build_preset_library(portal)
        assert unwired == []
        # Must survive the YAML trip the library store puts it through.
        document = yaml.safe_load(yaml.safe_dump(document, allow_unicode=True))
        assert document["dependencies"] == ["urn:test:portals:lib"]

        preset_data = document["objects"]["portal_presets"][0]
        importer = PortalPresetImporter(preset_data)
        assert importer.init() is None
        importer.import_portal_preset(catalog["library"])

        preset = PortalPreset.objects.get(urn=preset_data["urn"])
        items = preset.content["sections"][0]["items"]

        assert preset.library_id == catalog["library"].id
        assert items[0]["target"]["framework"] == str(catalog["fw"].id)
        assert items[1]["target"]["quick_form"] == str(catalog["qf"].id)
        assert items[2]["target"]["model"] == "incidents"

    def test_loading_without_the_dependency_leaves_the_tile_unwired(self, catalog):
        preset_data = {
            "urn": "urn:test:portals:portal_preset:orphan",
            "ref_id": "orphan",
            "name": "Orphan",
            "content": {
                "sections": [
                    {
                        "items": [
                            {
                                "kind": "assessment",
                                "title": "Run the audit",
                                "target": {"framework_urn": "urn:test:absent:fw"},
                            }
                        ]
                    }
                ]
            },
        }
        importer = PortalPresetImporter(preset_data)
        assert importer.init() is None
        importer.import_portal_preset(catalog["library"])

        preset = PortalPreset.objects.get(urn=preset_data["urn"])
        assert "framework" not in preset.content["sections"][0]["items"][0]["target"]

    def test_unloading_drops_the_catalog_entry_but_never_a_live_portal(self, catalog):
        portal = _portal(
            catalog, [{"kind": "create", "target": {"model": "incidents"}}]
        )
        user_authored = PortalPreset.objects.create(
            name="Mine", folder=catalog["folder"], content=portal.content
        )
        preset = PortalPreset.objects.create(
            name="Loaded design",
            urn="urn:test:portals:portal_preset:p",
            folder=catalog["folder"],
            library=catalog["library"],
            content=portal.content,
        )

        catalog["library"].delete()

        assert not PortalPreset.objects.filter(pk=preset.pk).exists()
        assert PortalPreset.objects.filter(pk=user_authored.pk).exists()
        assert Portal.objects.filter(pk=portal.pk).exists()

    def test_a_second_load_refreshes_in_place(self, catalog):
        preset_data = {
            "urn": "urn:test:portals:portal_preset:twice",
            "ref_id": "twice",
            "name": "Onboarding",
            "content": {"sections": [{"items": []}]},
        }
        PortalPresetImporter(preset_data).import_portal_preset(catalog["library"])
        PortalPresetImporter(
            {**preset_data, "name": "Onboarding v2"}
        ).import_portal_preset(catalog["library"])

        presets = PortalPreset.objects.filter(urn=preset_data["urn"])
        assert [p.name for p in presets] == ["Onboarding v2"]


@pytest.mark.django_db
class TestPresetValidation:
    @pytest.mark.parametrize(
        "content,expected",
        [
            ({"sections": []}, "non-empty"),
            ({"sections": [{"items": "nope"}]}, "list of objects"),
            ("not-an-object", "content must be an object"),
        ],
    )
    def test_malformed_content_is_rejected(self, content, expected):
        importer = PortalPresetImporter(
            {
                "urn": "urn:test:portals:portal_preset:bad",
                "ref_id": "bad",
                "content": content,
            }
        )

        assert expected in importer.init()

    def test_missing_identity_is_rejected(self):
        importer = PortalPresetImporter({"content": {"sections": [{"items": []}]}})

        error = importer.init()
        assert "ref_id" in error and "urn" in error


@pytest.mark.django_db
class TestPublishGate:
    """An incomplete tile blocks publishing, not saving."""

    def _serializer(self, catalog, instance=None, **data):
        from portals.serializers import PortalWriteSerializer

        payload = {"name": "P", "folder": str(catalog["folder"].id), **data}
        return PortalWriteSerializer(instance, data=payload)

    def _half_wired(self):
        return {
            "sections": [
                {"items": [{"kind": "assessment", "title": "Audit", "target": {}}]}
            ]
        }

    def test_a_half_wired_design_saves_as_a_draft(self, catalog):
        serializer = self._serializer(catalog, content=self._half_wired())

        assert serializer.is_valid(), serializer.errors

    def test_publishing_a_half_wired_design_is_refused(self, catalog):
        serializer = self._serializer(
            catalog, content=self._half_wired(), status="published"
        )

        assert not serializer.is_valid()
        assert "Audit" in str(serializer.errors["status"])

    def test_publishing_is_checked_against_stored_content_too(self, catalog):
        portal = Portal.objects.create(
            name="P", folder=catalog["folder"], content=self._half_wired()
        )
        # Only `status` is sent, so the gate has to reach for the instance's content.
        serializer = self._serializer(catalog, instance=portal, status="published")

        assert not serializer.is_valid()
        assert "Audit" in str(serializer.errors["status"])

    def test_a_wired_design_publishes(self, catalog):
        serializer = self._serializer(
            catalog,
            status="published",
            content={
                "sections": [
                    {
                        "items": [
                            {
                                "kind": "assessment",
                                "target": {"framework": str(catalog["fw"].id)},
                            }
                        ]
                    }
                ]
            },
        )

        assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
class TestLibraryUpdateRefresh:
    def _stored(self, catalog, version, preset_name):
        from core.models import StoredLibrary

        return StoredLibrary.objects.create(
            name="Catalog",
            urn=catalog["library"].urn,
            ref_id="CAT",
            version=version,
            locale="en",
            default_locale=True,
            folder=catalog["folder"],
            content={
                "portal_presets": [
                    {
                        "urn": "urn:test:portals:portal_preset:refreshed",
                        "ref_id": "refreshed",
                        "name": preset_name,
                        "content": {"sections": [{"items": []}]},
                    }
                ]
            },
        )

    def test_a_newer_version_refreshes_the_entry_in_place(self, catalog):
        from core.models import LibraryUpdater

        PortalPresetImporter(
            {
                "urn": "urn:test:portals:portal_preset:refreshed",
                "ref_id": "refreshed",
                "name": "v1",
                "content": {"sections": [{"items": []}]},
            }
        ).import_portal_preset(catalog["library"])

        LibraryUpdater(
            catalog["library"], self._stored(catalog, 2, "v2")
        ).update_portal_presets()

        presets = PortalPreset.objects.filter(
            urn="urn:test:portals:portal_preset:refreshed"
        )
        assert [(p.name, p.version) for p in presets] == [("v2", 2)]

    def test_a_refresh_does_not_touch_portals_cloned_from_it(self, catalog):
        from core.models import LibraryUpdater

        PortalPresetImporter(
            {
                "urn": "urn:test:portals:portal_preset:refreshed",
                "ref_id": "refreshed",
                "name": "v1",
                "content": {"sections": [{"title": "Original", "items": []}]},
            }
        ).import_portal_preset(catalog["library"])
        preset = PortalPreset.objects.get(
            urn="urn:test:portals:portal_preset:refreshed"
        )
        clone = Portal.objects.create(
            name="Live", folder=catalog["folder"], content=preset.content
        )

        LibraryUpdater(
            catalog["library"], self._stored(catalog, 2, "v2")
        ).update_portal_presets()
        clone.refresh_from_db()

        assert clone.content["sections"][0]["title"] == "Original"
