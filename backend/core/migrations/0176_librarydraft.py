# Library builder: add the LibraryDraft model, wrap any in-flight editing
# drafts of the retired standalone editors into LibraryDrafts, then drop the
# EditableMixin columns. The three steps live in one migration so they run in
# order and atomically: the model must exist before the data step reads/writes
# it, and the editing_draft columns must survive until the data step has
# consumed them.
#
# Data-step scope (deliberate, see the library-builder design note):
# - Framework WIP (library-less; the old editor only edited those): the
#   editor-doc blob is converted into a draft document. Missing URNs are
#   backfilled onto the live rows by row id first, so a later publish
#   updates those very rows in place (audits untouched).
# - Custom risk-matrix WIP: the WIP definition is wrapped into a draft,
#   the matrix URN minted onto the live row (bare family URN).
# - User-authored preset WIP (urn-less rows): the editor doc already IS the
#   builder's preset document shape, so it wraps directly. The `:preset:` URN
#   is minted onto the live row and the draft frozen, so a later publish
#   adopts that same row in place (no duplicate), like frameworks and matrices.
# - Library-backed matrix WIP and library-loaded preset WIP are logged and
#   skipped: their live/published state is untouched.
#
# Finished library-less frameworks WITHOUT WIP are not auto-wrapped — the
# on-demand "adopt a live framework" action covers them.
#
# This data migration imports two pure document helpers from the app
# (editor_doc_to_framework_object, urn_safe_leaf). They operate on plain
# dicts, never on models, so historical-model integrity is preserved.

import re

import django.core.validators
import django.db.models.deletion
import iam.models
import uuid
from django.db import migrations, models
from django.utils.timezone import now


def _token(value, fallback):
    token = re.sub(r"[^a-z0-9_-]+", "-", str(value or "").lower()).strip("-")
    return token or fallback


def _dedup_urn(model, candidate, exclude_id=None):
    base, suffix = candidate, 2
    queryset = model.objects.filter(urn=candidate)
    if exclude_id:
        queryset = queryset.exclude(id=exclude_id)
    while queryset.exists():
        candidate = f"{base}-{suffix}"
        suffix += 1
        queryset = model.objects.filter(urn=candidate)
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
    return candidate


def _wrap_framework_drafts(apps, root):
    from library.framework_editor import editor_doc_to_framework_object

    Framework = apps.get_model("core", "Framework")
    RequirementNode = apps.get_model("core", "RequirementNode")
    Question = apps.get_model("core", "Question")
    QuestionChoice = apps.get_model("core", "QuestionChoice")
    LibraryDraft = apps.get_model("core", "LibraryDraft")

    for framework in Framework.objects.exclude(editing_draft=None):
        label = f"framework {framework.id} ({framework.name!r})"
        if framework.library_id:
            print(f"[0176] skipping WIP on library-backed {label}")
            continue
        doc = framework.editing_draft or {}
        meta = doc.get("framework_meta") or {}

        packager = _token(meta.get("urn_namespace") or "custom", "custom")
        ref = _token(
            meta.get("ref_id") or framework.ref_id or framework.name,
            f"framework-{str(framework.id)[:8]}",
        )
        if framework.urn:
            match = re.match(
                r"^urn:([a-z0-9_-]+):[a-z0-9_.-]+:framework:(.+)$",
                framework.urn.lower(),
            )
            if match:
                packager, ref = match.group(1), _token(match.group(2), ref)
        else:
            framework.urn = _dedup_urn(
                Framework,
                f"urn:{packager}:risk:framework:{ref}",
                exclude_id=framework.id,
            )
            framework.save(update_fields=["urn"])

        # Backfill URNs onto live rows by row id: the editor doc records
        # carry both, so a later publish updates these very rows.
        for model, records in (
            (RequirementNode, doc.get("nodes") or []),
            (Question, doc.get("questions") or []),
            (QuestionChoice, doc.get("choices") or []),
        ):
            for record in records:
                if not (record.get("id") and record.get("urn")):
                    continue
                try:
                    row = model.objects.filter(id=record["id"], urn=None).first()
                except Exception:  # editor-local ids ("tmp-…") are not UUIDs
                    continue
                if (
                    row is not None
                    and not model.objects.filter(
                        urn=str(record["urn"]).lower()
                    ).exists()
                ):
                    row.urn = str(record["urn"]).lower()
                    row.save(update_fields=["urn"])

        # Every URN already present in the doc must survive conversion
        # verbatim (that is what matches the backfilled live rows), so the
        # `existing` skeleton declares them all.
        choices_by_question = {}
        for record in doc.get("choices") or []:
            if record.get("urn"):
                choices_by_question.setdefault(
                    str(record.get("question_id") or ""), []
                ).append({"urn": str(record["urn"]).lower()})
        questions_by_node = {}
        for record in doc.get("questions") or []:
            if not record.get("urn"):
                continue
            q_urn = str(record["urn"]).lower()
            questions_by_node.setdefault(
                str(record.get("requirement_node_id") or ""), {}
            )[q_urn] = {
                "choices": choices_by_question.get(str(record.get("id") or ""), [])
                + choices_by_question.get(str(record.get("urn") or ""), [])
            }
        existing_nodes = []
        for record in doc.get("nodes") or []:
            if not record.get("urn"):
                continue
            existing_nodes.append(
                {
                    "urn": str(record["urn"]).lower(),
                    "questions": questions_by_node.get(str(record.get("id") or ""), {})
                    or questions_by_node.get(str(record.get("urn") or ""), {}),
                }
            )
        try:
            framework_object = editor_doc_to_framework_object(
                doc,
                existing={
                    "urn": framework.urn.lower(),
                    "requirement_nodes": existing_nodes,
                },
            )
        except Exception as exc:  # malformed WIP: keep live state, log loudly
            print(f"[0176] could NOT wrap WIP of {label}: {exc}")
            continue

        library_urn = framework.urn.lower().replace(":framework:", ":library:", 1)
        if LibraryDraft.objects.filter(urn=library_urn).exists():
            print(f"[0176] draft already exists for {label} ({library_urn}), skipping")
            continue
        LibraryDraft.objects.create(
            name=meta.get("name") or framework.name,
            description=meta.get("description") or framework.description,
            folder=root,
            packager=packager,
            ref_id=ref,
            locale=meta.get("locale") or "en",
            version=1,
            provider=framework.provider or packager,
            content={"frameworks": [framework_object]},
            dependencies=[],
            urn=library_urn,
            # The live rows carry this family: identity frozen from the start.
            first_published_at=now(),
        )
        framework.editing_draft = None
        framework.save(update_fields=["editing_draft"])
        print(f"[0176] wrapped WIP of {label} into draft {library_urn}")


def _wrap_matrix_drafts(apps, root):
    RiskMatrix = apps.get_model("core", "RiskMatrix")
    LibraryDraft = apps.get_model("core", "LibraryDraft")

    for matrix in RiskMatrix.objects.exclude(editing_draft=None):
        label = f"risk matrix {matrix.id} ({matrix.name!r})"
        if matrix.library_id:
            print(f"[0176] skipping WIP on library-backed {label}")
            continue
        definition = matrix.editing_draft or {}
        ref = _token(matrix.ref_id or matrix.name, f"matrix-{str(matrix.id)[:8]}")
        if not matrix.urn:
            matrix.urn = _dedup_urn(
                RiskMatrix, f"urn:custom:risk:matrix:{ref}", exclude_id=matrix.id
            )
            matrix.save(update_fields=["urn"])
        library_urn = f"urn:custom:risk:library:{ref}"
        if LibraryDraft.objects.filter(urn=library_urn).exists():
            print(f"[0176] draft already exists for {label} ({library_urn}), skipping")
            continue
        matrix_object = {
            "urn": matrix.urn.lower(),
            "ref_id": matrix.ref_id or ref,
            "name": matrix.name,
            "description": matrix.description,
        }
        for key in ("probability", "impact", "risk", "grid", "strength_of_knowledge"):
            if key in definition:
                matrix_object[key] = definition[key]
        LibraryDraft.objects.create(
            name=matrix.name,
            description=matrix.description,
            folder=root,
            packager="custom",
            ref_id=ref,
            locale="en",
            version=1,
            provider="custom",
            content={"risk_matrices": [matrix_object]},
            dependencies=[],
            urn=library_urn,
            first_published_at=now(),
        )
        matrix.editing_draft = None
        matrix.save(update_fields=["editing_draft"])
        print(f"[0176] wrapped WIP of {label} into draft {library_urn}")


def _wrap_preset_drafts(apps, root):
    Preset = apps.get_model("core", "Preset")
    LibraryDraft = apps.get_model("core", "LibraryDraft")

    for preset in Preset.objects.exclude(editing_draft=None):
        label = f"preset {preset.id} ({preset.name!r})"
        if preset.urn:
            print(f"[0176] skipping WIP on library-loaded {label}")
            continue
        doc = preset.editing_draft or {}
        meta = doc.get("journey_meta") or {}
        name = meta.get("name") or preset.name

        # Mint the preset family URN onto the live row and freeze the draft's
        # identity, mirroring the matrix wrap: a later publish then adopts THAT
        # very row in place (upsert_preset_from_stored_library keys on the
        # `:preset:` URN derived from the library URN) instead of creating a
        # duplicate Preset. The live row becomes read-only in the catalog
        # (urn != None), now managed through the draft.
        ref = _token(name, f"preset-{str(preset.id)[:8]}")
        library_urn = f"urn:custom:risk:library:{ref}"
        suffix = 2
        while LibraryDraft.objects.filter(urn=library_urn).exists():
            library_urn = f"urn:custom:risk:library:{ref}-{suffix}"
            suffix += 1
        ref = library_urn.rsplit(":", 1)[-1]
        preset_urn = library_urn.replace(":library:", ":preset:", 1)

        # The editor doc {journey_meta, scaffolded_objects, steps} is the
        # builder's preset document shape (see LibraryDraftViewSet's
        # preset-editor bridge); profile/feature_flags come from the live row.
        preset_object = {
            "name": name,
            "description": meta.get("description") or preset.description or "",
            "scaffolded_objects": list(doc.get("scaffolded_objects") or []),
            "journey": {"steps": list(doc.get("steps") or [])},
        }
        if preset.profile:
            preset_object["profile"] = preset.profile
        if preset.feature_flags:
            preset_object["feature_flags"] = preset.feature_flags

        LibraryDraft.objects.create(
            name=name,
            description=preset_object["description"],
            folder=root,
            packager="custom",
            ref_id=ref,
            locale="en",
            version=1,
            provider=preset.provider or "custom",
            content={"preset": preset_object},
            dependencies=[],
            urn=library_urn,
            # The live row carries the family URN: identity frozen from the
            # start so publish adopts that row rather than minting a new one.
            first_published_at=now(),
        )
        preset.urn = preset_urn
        preset.editing_draft = None
        preset.save(update_fields=["urn", "editing_draft"])
        print(f"[0176] wrapped WIP of {label} into draft {library_urn}")


def wrap_editing_drafts(apps, schema_editor):
    Folder = apps.get_model("iam", "Folder")
    root = Folder.objects.filter(content_type="GL", parent_folder=None).first()
    if root is None:
        return  # fresh install: nothing to wrap

    _wrap_framework_drafts(apps, root)
    _wrap_matrix_drafts(apps, root)
    _wrap_preset_drafts(apps, root)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0175_customdochtmltemplate_objectclassification_and_more"),
        ("iam", "0023_alter_folder_content_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="LibraryDraft",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created at"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated at"),
                ),
                (
                    "is_published",
                    models.BooleanField(default=False, verbose_name="published"),
                ),
                ("name", models.CharField(max_length=200, verbose_name="Name")),
                (
                    "description",
                    models.TextField(blank=True, null=True, verbose_name="Description"),
                ),
                (
                    "packager",
                    models.CharField(
                        max_length=100,
                        validators=[
                            django.core.validators.RegexValidator(
                                message="invalidLibraryIdentity", regex="^[a-z0-9_-]+$"
                            )
                        ],
                        verbose_name="Packager",
                    ),
                ),
                (
                    "ref_id",
                    models.CharField(
                        max_length=100,
                        validators=[
                            django.core.validators.RegexValidator(
                                message="invalidLibraryIdentity", regex="^[a-z0-9_-]+$"
                            )
                        ],
                        verbose_name="Reference ID",
                    ),
                ),
                (
                    "urn",
                    models.CharField(
                        blank=True, max_length=255, null=True, verbose_name="URN"
                    ),
                ),
                (
                    "locale",
                    models.CharField(
                        default="en", max_length=100, verbose_name="Locale"
                    ),
                ),
                (
                    "version",
                    models.IntegerField(
                        default=1,
                        validators=[django.core.validators.MinValueValidator(1)],
                        verbose_name="Version",
                    ),
                ),
                (
                    "provider",
                    models.CharField(
                        blank=True, max_length=200, null=True, verbose_name="Provider"
                    ),
                ),
                (
                    "copyright",
                    models.CharField(
                        blank=True, max_length=4096, null=True, verbose_name="Copyright"
                    ),
                ),
                ("publication_date", models.DateField(blank=True, null=True)),
                (
                    "annotation",
                    models.TextField(blank=True, null=True, verbose_name="Annotation"),
                ),
                ("translations", models.JSONField(blank=True, default=dict)),
                ("dependencies", models.JSONField(blank=True, default=list)),
                ("labels", models.JSONField(blank=True, default=list)),
                ("content", models.JSONField(blank=True, default=dict)),
                ("first_published_at", models.DateTimeField(blank=True, null=True)),
                ("last_published_at", models.DateTimeField(blank=True, null=True)),
                (
                    "folder",
                    models.ForeignKey(
                        default=iam.models.Folder.get_root_folder_id,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s_folder",
                        to="iam.folder",
                    ),
                ),
            ],
            options={
                "verbose_name": "Library draft",
                "verbose_name_plural": "Library drafts",
            },
        ),
        migrations.RunPython(wrap_editing_drafts, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="framework",
            name="editing_draft",
        ),
        migrations.RemoveField(
            model_name="framework",
            name="editing_history",
        ),
        migrations.RemoveField(
            model_name="framework",
            name="editing_version",
        ),
        migrations.RemoveField(
            model_name="preset",
            name="editing_draft",
        ),
        migrations.RemoveField(
            model_name="preset",
            name="editing_history",
        ),
        migrations.RemoveField(
            model_name="preset",
            name="editing_version",
        ),
        migrations.RemoveField(
            model_name="riskmatrix",
            name="editing_draft",
        ),
        migrations.RemoveField(
            model_name="riskmatrix",
            name="editing_history",
        ),
        migrations.RemoveField(
            model_name="riskmatrix",
            name="editing_version",
        ),
    ]
