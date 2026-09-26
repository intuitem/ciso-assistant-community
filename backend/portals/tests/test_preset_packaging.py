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

    def test_a_publication_wired_tile_travels_as_its_quick_form(self, catalog):
        """The editor's recommended wiring for outside respondents is a publication
        alone. The publication is local, the form behind it is not."""
        from core.models import QuickFormPublication

        publication = QuickFormPublication.objects.create(
            name="Access requests",
            folder=catalog["folder"],
            quick_form=catalog["qf"],
        )
        portal = _portal(
            catalog,
            [
                {
                    "kind": "quickForm",
                    "title": "Ask for access",
                    "target": {"publication": str(publication.id)},
                }
            ],
        )

        exported, unwired = dereference(portal.content)
        assert unwired == []
        assert exported["sections"][0]["items"][0]["target"] == {
            "quick_form_urn": "urn:test:portals:qf"
        }

        local, unwired = dereference(portal.content, keep_local_ids=True)
        assert unwired == []
        assert local["sections"][0]["items"][0]["target"] == {
            "publication": str(publication.id),
            "quick_form_urn": "urn:test:portals:qf",
        }

    def test_a_publication_that_is_gone_is_reported(self, catalog):
        portal = _portal(
            catalog,
            [
                {
                    "kind": "quickForm",
                    "title": "Ask for access",
                    "target": {"publication": "00000000-0000-0000-0000-000000000000"},
                }
            ],
        )
        content, unwired = dereference(portal.content)

        assert len(unwired) == 1
        assert "publication" in unwired[0]
        assert content["sections"][0]["items"][0]["target"] == {}

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

    def test_a_local_template_keeps_an_unportable_framework_wired(self, catalog):
        """Save-as-template stays on this instance, so a framework with no URN keeps
        its id: the design still works here even if it could not travel."""
        local_only = Framework.objects.create(
            name="Homegrown", folder=catalog["folder"], locale="en", default_locale=True
        )
        portal = _portal(
            catalog,
            [{"kind": "assessment", "target": {"framework": str(local_only.id)}}],
        )
        content, unwired = dereference(portal.content, keep_local_ids=True)
        target = content["sections"][0]["items"][0]["target"]

        assert unwired == []
        assert target == {"framework": str(local_only.id)}

    def test_an_id_that_is_not_a_uuid_is_unwired_not_a_crash(self, catalog):
        portal = _portal(
            catalog,
            [
                {
                    "kind": "assessment",
                    "title": "Legacy",
                    "target": {"framework": "legacy-id"},
                }
            ],
        )
        content, unwired = dereference(portal.content)

        assert len(unwired) == 1
        assert "framework" not in content["sections"][0]["items"][0]["target"]

    def test_the_id_decides_what_travels_not_a_urn_left_next_to_it(self, catalog):
        """The editor rebinds only the id. A tile once wired to the library
        framework and re-pointed at a homegrown one must stay homegrown."""
        homegrown = Framework.objects.create(
            name="Homegrown", folder=catalog["folder"], locale="en", default_locale=True
        )
        portal = _portal(
            catalog,
            [
                {
                    "kind": "assessment",
                    "title": "Audit",
                    "target": {
                        "framework": str(homegrown.id),
                        "framework_urn": catalog["fw"].urn,
                    },
                }
            ],
        )

        template, _ = dereference(portal.content, keep_local_ids=True)
        cloned, unwired = resolve(template)
        assert unwired == []
        assert cloned["sections"][0]["items"][0]["target"] == {
            "framework": str(homegrown.id)
        }

        exported, unwired = dereference(portal.content)
        assert len(unwired) == 1
        assert exported["sections"][0]["items"][0]["target"] == {}

    def test_an_unresolved_urn_travels_on_until_something_is_picked(self, catalog):
        portal = _portal(
            catalog,
            [
                {
                    "kind": "assessment",
                    "target": {"framework_urn": "urn:test:absent:fw"},
                }
            ],
        )

        exported, _ = dereference(portal.content)

        assert exported["sections"][0]["items"][0]["target"] == {
            "framework_urn": "urn:test:absent:fw"
        }

    def test_the_publication_decides_the_form_as_it_does_on_click(self, catalog):
        """Picking a publication hides the inline form select without clearing it;
        the tile runs the publication's form, so that is the one that travels."""
        from core.models import QuickFormPublication

        other = QuickForm.objects.create(
            name="Laptop request",
            urn="urn:test:portals:qf2",
            ref_id="QF2",
            folder=catalog["folder"],
            library=catalog["library"],
            locale="en",
            default_locale=True,
        )
        publication = QuickFormPublication.objects.create(
            name="Laptops", folder=catalog["folder"], quick_form=other
        )
        portal = _portal(
            catalog,
            [
                {
                    "kind": "quickForm",
                    "title": "Ask",
                    "target": {
                        "publication": str(publication.id),
                        "quick_form": str(catalog["qf"].id),
                    },
                }
            ],
        )

        exported, unwired = dereference(portal.content)

        assert unwired == []
        assert exported["sections"][0]["items"][0]["target"] == {
            "quick_form_urn": other.urn
        }

    def test_a_local_template_keeps_the_tiles_domain_and_reviewers(self, catalog):
        target = {
            "quick_form": str(catalog["qf"].id),
            "folder": str(catalog["folder"].id),
            "reviewers": ["an-actor-id"],
        }
        portal = _portal(catalog, [{"kind": "quickForm", "target": target}])

        template, unwired = dereference(portal.content, keep_local_ids=True)

        assert unwired == []
        assert template["sections"][0]["items"][0]["target"] == {
            "quick_form_urn": catalog["qf"].urn,
            "folder": target["folder"],
            "reviewers": target["reviewers"],
        }


@pytest.mark.django_db
class TestResolve:
    def test_urns_become_local_ids(self, catalog):
        """The URN goes once resolved: the editor only ever rewrites the id, so a
        URN left next to it would go stale and override the author's next pick."""
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
        assert target == {"framework": str(catalog["fw"].id)}

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

    def test_an_id_that_travelled_with_an_unloaded_urn_is_dropped(self, catalog):
        """A hand-written preset may carry an id next to the URN; on another
        instance that id is dangling, and would only make the tile look wired."""
        content, _unwired = resolve(
            {
                "sections": [
                    {
                        "items": [
                            {
                                "kind": "assessment",
                                "target": {
                                    "framework": "00000000-0000-0000-0000-000000000000",
                                    "framework_urn": "urn:test:absent:fw",
                                },
                            }
                        ]
                    }
                ]
            }
        )

        assert "framework" not in content["sections"][0]["items"][0]["target"]


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
        assert "dependencies" not in document

        preset_data = document["objects"]["portal_presets"][0]
        importer = PortalPresetImporter(preset_data)
        assert importer.init() is None
        importer.import_portal_preset(catalog["library"])

        preset = PortalPreset.objects.get(urn=preset_data["urn"])
        # Stored as shipped; the tiles are wired when a portal is cloned from it.
        assert preset.content == preset_data["content"]
        items = resolve(preset.content)[0]["sections"][0]["items"]

        assert preset.library_id == catalog["library"].id
        assert items[0]["target"]["framework"] == str(catalog["fw"].id)
        assert items[1]["target"]["quick_form"] == str(catalog["qf"].id)
        assert items[2]["target"]["model"] == "incidents"

    def test_an_exported_portal_loads_through_the_library_store(self, catalog):
        """The whole path a shipped design takes: YAML in the store, load, a preset
        owned by the new library with its tiles wired to the local rows."""
        from core.models import StoredLibrary

        portal = _portal(
            catalog,
            [
                {
                    "id": "t1",
                    "kind": "assessment",
                    "title": "Run the audit",
                    "target": {"framework": str(catalog["fw"].id)},
                }
            ],
        )
        portal.name = "Shipped design"
        portal.save()
        document, _unwired = build_preset_library(portal)

        stored, error = StoredLibrary.store_library_content(
            yaml.safe_dump(document, allow_unicode=True).encode("utf-8")
        )
        assert error is None, error
        assert stored.objects_meta == {"portal_presets": 1}
        assert stored.load() is None

        library = LoadedLibrary.objects.get(urn=document["urn"])
        preset = PortalPreset.objects.get(
            urn=document["objects"]["portal_presets"][0]["urn"]
        )
        assert preset.library_id == library.id
        assert preset.provider == "personal"
        assert not library.dependencies.exists()
        target = preset.content["sections"][0]["items"][0]["target"]
        assert target == {"framework_urn": "urn:test:portals:fw"}
        assert resolve(preset.content)[0]["sections"][0]["items"][0]["target"] == {
            "framework": str(catalog["fw"].id)
        }

    def test_a_stored_newer_version_updates_the_loaded_preset(self, catalog):
        from core.models import StoredLibrary

        portal = _portal(
            catalog, [{"kind": "create", "target": {"model": "incidents"}}]
        )
        portal.name = "Updated design"
        portal.save()
        document, _unwired = build_preset_library(portal)
        stored, error = StoredLibrary.store_library_content(
            yaml.safe_dump(document, allow_unicode=True).encode("utf-8")
        )
        assert error is None, error
        assert stored.load() is None

        # Edit and export again: the next version, loadable as an update.
        portal.name = "Updated design v2"
        portal.content["sections"][0]["title"] = "Start over"
        portal.save()
        document, _unwired = build_preset_library(portal)
        assert document["version"] == 2
        stored_v2, error = StoredLibrary.store_library_content(
            yaml.safe_dump(document, allow_unicode=True).encode("utf-8")
        )
        assert error is None, error
        library = LoadedLibrary.objects.get(urn=document["urn"])
        assert library.update() is None

        library.refresh_from_db()
        preset = PortalPreset.objects.get(
            urn=document["objects"]["portal_presets"][0]["urn"]
        )
        assert library.version == 2
        assert (preset.name, preset.version) == ("Updated design v2", 2)
        assert preset.content["sections"][0]["title"] == "Start over"
        assert preset.library_id == library.id

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
        content, unwired = resolve(preset.content)
        assert "framework" not in content["sections"][0]["items"][0]["target"]
        assert len(unwired) == 1

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
class TestExportIdentity:
    def _store(self, document):
        from core.models import StoredLibrary

        return StoredLibrary.store_library_content(
            yaml.safe_dump(document, allow_unicode=True).encode("utf-8")
        )

    def test_identity_follows_the_portal_not_its_name(self, catalog):
        first = _portal(catalog, [])
        before, _ = build_preset_library(first)
        first.name = "Renamed"
        first.save()
        after, _ = build_preset_library(first)
        assert after["urn"] == before["urn"]

        # Names a slug cannot tell apart must not collide.
        a = Portal.objects.create(name="Портал поставщиков", folder=catalog["folder"])
        b = Portal.objects.create(name="供应商门户", folder=catalog["folder"])
        assert build_preset_library(a)[0]["urn"] != build_preset_library(b)[0]["urn"]

    def test_a_long_name_still_exports_a_loadable_library(self, catalog):
        portal = _portal(
            catalog, [{"kind": "create", "target": {"model": "incidents"}}]
        )
        portal.name = "Security operations onboarding portal " + "x" * 150
        portal.save()

        stored, error = self._store(build_preset_library(portal)[0])

        assert error is None, error
        assert stored.load() is None

    def test_the_version_moves_only_when_what_ships_changes(self, catalog):
        portal = _portal(
            catalog, [{"kind": "create", "target": {"model": "incidents"}}]
        )

        assert build_preset_library(portal)[0]["version"] == 1
        assert build_preset_library(portal)[0]["version"] == 1

        portal.content["sections"][0]["title"] = "Edited"
        portal.save()
        assert build_preset_library(portal)[0]["version"] == 2

        # A settings change ships nothing new.
        portal.enabled = False
        portal.save()
        assert build_preset_library(portal)[0]["version"] == 2

    def test_a_design_loads_without_the_libraries_behind_its_tiles(self, catalog):
        """References are soft: a missing library leaves the tile unwired at Use
        time instead of failing the load."""
        portal = _portal(
            catalog,
            [
                {
                    "id": "t1",
                    "kind": "assessment",
                    "title": "Run the audit",
                    "target": {"framework": str(catalog["fw"].id)},
                }
            ],
        )
        document, _ = build_preset_library(portal)
        assert "dependencies" not in document
        # The receiving instance does not have the framework's library.
        portal.delete()
        catalog["library"].delete()

        stored, error = self._store(document)
        assert error is None, error
        assert stored.load() is None

        preset = PortalPreset.objects.get(
            urn=document["objects"]["portal_presets"][0]["urn"]
        )
        content, unwired = resolve(preset.content)
        assert "framework" not in content["sections"][0]["items"][0]["target"]
        assert len(unwired) == 1


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
                "name": "Bad",
                "content": content,
            }
        )

        assert expected in importer.init()

    def test_missing_identity_is_rejected(self):
        importer = PortalPresetImporter({"content": {"sections": [{"items": []}]}})

        error = importer.init()
        assert "ref_id" in error and "urn" in error and "name" in error

    @pytest.mark.parametrize(
        "field,value",
        [
            ("name", "x" * 201),
            ("name", ""),
            ("name", 42),
            ("urn", "urn:test:" + "x" * 250),
            ("ref_id", "x" * 256),
        ],
    )
    def test_a_column_postgres_would_reject_fails_the_load_everywhere(
        self, field, value
    ):
        """PostgreSQL raises on an oversized CharField and SQLite stores it; the
        importer has to give the same answer on both."""
        importer = PortalPresetImporter(
            {
                "urn": "urn:test:portals:portal_preset:long",
                "ref_id": "long",
                "name": "Long",
                "content": {"sections": [{"items": []}]},
                field: value,
            }
        )

        assert field in importer.init()

    def test_a_urn_another_library_ships_is_refused(self, catalog):
        preset_data = {
            "urn": "urn:test:portals:portal_preset:shared",
            "ref_id": "shared",
            "name": "Shared",
            "content": {"sections": [{"items": []}]},
        }
        PortalPresetImporter(
            preset_data, library_urn=catalog["library"].urn
        ).import_portal_preset(catalog["library"])

        again = PortalPresetImporter(preset_data, library_urn=catalog["library"].urn)
        other = PortalPresetImporter(preset_data, library_urn="urn:test:other:lib")

        assert again.init() is None
        assert catalog["library"].urn in other.init()

    def test_another_locale_of_the_same_library_is_refused(self, catalog):
        """Taking the row over would re-home it to the other locale's library, and
        unloading that one would cascade the preset away from this one."""
        preset_data = {
            "urn": "urn:test:portals:portal_preset:localized",
            "ref_id": "localized",
            "name": "Localized",
            "content": {"sections": [{"items": []}]},
        }
        PortalPresetImporter(
            preset_data, library_urn=catalog["library"].urn, locale="en"
        ).import_portal_preset(catalog["library"])

        french = PortalPresetImporter(
            preset_data, library_urn=catalog["library"].urn, locale="fr"
        )

        assert "(en)" in french.init()


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

    def test_a_published_portal_refuses_incomplete_content(self, catalog):
        """The direction the editor's Save button hits: the portal is live, and the
        PATCH carries content only."""
        portal = Portal.objects.create(
            name="P",
            folder=catalog["folder"],
            status=Portal.Status.PUBLISHED,
            content={"sections": []},
        )
        from portals.serializers import PortalWriteSerializer

        serializer = PortalWriteSerializer(
            portal, data={"content": self._half_wired()}, partial=True
        )

        assert not serializer.is_valid()
        assert "Audit" in str(serializer.errors["status"])

    def test_launchable_tiles_get_an_id_on_save(self, catalog):
        """A click finds its tile by id; content that arrives without one (a
        library preset, the API) must not produce tiles that 404."""
        serializer = self._serializer(
            catalog,
            content={
                "sections": [
                    {
                        "items": [
                            {"kind": "assessment", "target": {}},
                            {"kind": "quickForm", "target": {}},
                            {"id": "kept", "kind": "assessment", "target": {}},
                            {"kind": "create", "target": {"model": "incidents"}},
                        ]
                    }
                ]
            },
        )

        assert serializer.is_valid(), serializer.errors
        items = serializer.validated_data["content"]["sections"][0]["items"]
        assert items[0]["id"] and items[1]["id"] and items[0]["id"] != items[1]["id"]
        assert items[2]["id"] == "kept"
        assert "id" not in items[3]

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
    def _stored(self, catalog, version, preset_name, presets=None, urn=None):
        from core.models import StoredLibrary

        return StoredLibrary.objects.create(
            name="Catalog",
            urn=urn or catalog["library"].urn,
            ref_id="CAT",
            version=version,
            locale="en",
            default_locale=True,
            folder=catalog["folder"],
            content={
                "portal_presets": presets
                or [
                    {
                        "urn": "urn:test:portals:portal_preset:refreshed",
                        "ref_id": "refreshed",
                        "name": preset_name,
                        "content": {"sections": [{"items": []}]},
                    }
                ]
            },
        )

    def _update(self, library, stored):
        from core.models import LibraryUpdater

        return LibraryUpdater(library, stored).update_library()

    def test_a_newer_version_refreshes_the_entry_in_place(self, catalog):
        PortalPresetImporter(
            {
                "urn": "urn:test:portals:portal_preset:refreshed",
                "ref_id": "refreshed",
                "name": "v1",
                "content": {"sections": [{"items": []}]},
            }
        ).import_portal_preset(catalog["library"])

        assert self._update(catalog["library"], self._stored(catalog, 2, "v2")) is None

        presets = PortalPreset.objects.filter(
            urn="urn:test:portals:portal_preset:refreshed"
        )
        assert [(p.name, p.version) for p in presets] == [("v2", 2)]

    def test_a_preset_the_new_version_dropped_goes_with_it(self, catalog):
        PortalPresetImporter(
            {
                "urn": "urn:test:portals:portal_preset:dropped",
                "ref_id": "dropped",
                "name": "Dropped",
                "content": {"sections": [{"items": []}]},
            }
        ).import_portal_preset(catalog["library"])
        mine = PortalPreset.objects.create(
            name="Mine", folder=catalog["folder"], content={"sections": []}
        )

        assert self._update(catalog["library"], self._stored(catalog, 2, "v2")) is None

        urns = set(
            PortalPreset.objects.filter(library=catalog["library"]).values_list(
                "urn", flat=True
            )
        )
        assert urns == {"urn:test:portals:portal_preset:refreshed"}
        assert PortalPreset.objects.filter(pk=mine.pk).exists()

    def test_a_refresh_does_not_touch_portals_cloned_from_it(self, catalog):
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

        assert self._update(catalog["library"], self._stored(catalog, 2, "v2")) is None
        clone.refresh_from_db()

        assert clone.content["sections"][0]["title"] == "Original"

    def test_an_update_cannot_take_over_a_preset_another_library_ships(self, catalog):
        """The load refuses a URN another library owns; an update must too, or a
        new version of one library silently rewrites the other's catalog entry."""
        owned = {
            "urn": "urn:test:portals:portal_preset:owned",
            "ref_id": "owned",
            "name": "Owned by the catalog",
            "content": {"sections": [{"items": []}]},
        }
        PortalPresetImporter(
            owned, library_urn=catalog["library"].urn
        ).import_portal_preset(catalog["library"])
        other = LoadedLibrary.objects.create(
            name="Other",
            urn="urn:test:other:lib",
            ref_id="OTHER",
            version=1,
            locale="en",
            default_locale=True,
            folder=catalog["folder"],
        )

        error = self._update(
            other,
            self._stored(
                catalog,
                2,
                None,
                presets=[{**owned, "name": "Taken over"}],
                urn=other.urn,
            ),
        )

        assert catalog["library"].urn in error
        preset = PortalPreset.objects.get(urn=owned["urn"])
        assert (preset.name, preset.library_id) == (
            "Owned by the catalog",
            catalog["library"].id,
        )
        other.refresh_from_db()
        assert other.version == 1

    def test_an_update_gets_the_loads_content_checks_before_writing(self, catalog):
        error = self._update(
            catalog["library"],
            self._stored(
                catalog,
                2,
                None,
                presets=[
                    {
                        "urn": "urn:test:portals:portal_preset:bad",
                        "ref_id": "bad",
                        "name": "Bad",
                        "content": {"sections": [{"items": "nope"}]},
                    }
                ],
            ),
        )

        assert "list of objects" in error
        assert not PortalPreset.objects.filter(
            urn="urn:test:portals:portal_preset:bad"
        ).exists()
        catalog["library"].refresh_from_db()
        assert catalog["library"].version == 1


@pytest.mark.django_db
class TestTemplateEndpoints:
    """Save as template, then Use: the tile must come back wired."""

    @pytest.fixture
    def client(self, catalog):
        from core.apps import startup
        from global_settings.models import GlobalSettings
        from iam.models import User, UserGroup
        from knox.models import AuthToken
        from rest_framework.test import APIClient

        startup(sender=None, **{})
        GlobalSettings.objects.update_or_create(
            name=GlobalSettings.Names.FEATURE_FLAGS,
            defaults={"value": {"custom_portals": True, "quick_forms": True}},
        )
        user = User.objects.create_user(email="portal-admin@test.local")
        admin_group = UserGroup.objects.get(name="BI-UG-ADM")
        user.folder = admin_group.folder
        user.save()
        admin_group.user_set.add(user)
        client = APIClient()
        token = AuthToken.objects.create(user=user)
        client.credentials(HTTP_AUTHORIZATION=f"Token {token[1]}")
        return client

    def test_save_then_use_keeps_every_tile_wired(self, catalog, client):
        local_only = Framework.objects.create(
            name="Homegrown", folder=catalog["folder"], locale="en", default_locale=True
        )
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
                    "kind": "assessment",
                    "title": "Homegrown audit",
                    "target": {"framework": str(local_only.id)},
                },
                {
                    "id": "t3",
                    "kind": "quickForm",
                    "title": "Ask for access",
                    "target": {"quick_form": str(catalog["qf"].id)},
                },
            ],
        )

        saved = client.post(f"/api/portals/{portal.id}/save-as-preset/", {})
        assert saved.status_code == 201, saved.json()
        assert saved.json()["unwired"] == []

        used = client.post(
            "/api/portals/from-preset/", {"preset": saved.json()["id"]}, format="json"
        )
        assert used.status_code == 201, used.json()
        assert used.json()["unwired"] == []

        clone = Portal.objects.get(pk=used.json()["id"])
        items = clone.content["sections"][0]["items"]
        assert items[0]["target"]["framework"] == str(catalog["fw"].id)
        assert items[1]["target"]["framework"] == str(local_only.id)
        assert items[2]["target"]["quick_form"] == str(catalog["qf"].id)

    def test_a_second_template_from_the_same_portal_gets_its_own_name(
        self, catalog, client
    ):
        portal = _portal(catalog, [])

        first = client.post(f"/api/portals/{portal.id}/save-as-preset/", {})
        second = client.post(f"/api/portals/{portal.id}/save-as-preset/", {})

        assert first.json()["name"] == "Onboarding"
        assert second.json()["name"] == "Onboarding (2)"

    def test_an_oversized_name_is_a_400_on_every_database(self, catalog, client):
        portal = _portal(catalog, [])

        res = client.post(
            f"/api/portals/{portal.id}/save-as-preset/",
            {"name": "x" * 300},
            format="json",
        )

        assert res.status_code == 400
        assert "name" in res.json()

    def test_a_library_preset_without_tile_ids_clones_into_clickable_tiles(
        self, catalog, client
    ):
        """Use, then Publish before any Save: the clone's tiles must still launch."""
        PortalPresetImporter(
            {
                "urn": "urn:test:portals:portal_preset:noid",
                "ref_id": "noid",
                "name": "No ids",
                "content": {
                    "sections": [
                        {
                            "items": [
                                {
                                    "kind": "assessment",
                                    "title": "Run the audit",
                                    "target": {"framework_urn": catalog["fw"].urn},
                                }
                            ]
                        }
                    ]
                },
            },
            library_urn=catalog["library"].urn,
        ).import_portal_preset(catalog["library"])
        preset = PortalPreset.objects.get(urn="urn:test:portals:portal_preset:noid")

        used = client.post(
            "/api/portals/from-preset/", {"preset": str(preset.id)}, format="json"
        )
        assert used.status_code == 201, used.json()
        portal_id = used.json()["id"]
        published = client.patch(
            f"/api/portals/{portal_id}/", {"status": "published"}, format="json"
        )
        assert published.status_code == 200, published.json()

        item = Portal.objects.get(pk=portal_id).content["sections"][0]["items"][0]
        launched = client.post(
            f"/api/portals/{portal_id}/launch-assessment/",
            {"item": item["id"], "folder": str(catalog["folder"].id)},
            format="json",
        )
        assert launched.status_code == 200, launched.json()
