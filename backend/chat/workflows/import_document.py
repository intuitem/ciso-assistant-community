"""
Document import workflow.

The user attaches a tabular file (xlsx/csv) to a chat message; the workflow
digests it and prepares importing its rows as objects (applied controls,
findings…) through the data_wizard consumers.

Agentic experience, deterministic engine: parsing, column mapping, and
target detection are code. The LLM is only consulted for what the
deterministic layers can't resolve, and nothing is ever written without an
explicit user confirmation.

Steps:
    1. Digest the attached file (deterministic)
    2. Detect the target model, ask the user when ambiguous (pending_choice)
    3. For findings and risk scenarios: pick an existing assessment to update
       or a new one, plus the matrix a new risk assessment needs
    4. Map columns via data_wizard alias tables + model fields (deterministic)
    5. Dry-run through the consumer (rolled back) and narrate exact counts
    6. Confirmation card; apply happens in views.apply_import atomically
"""

import re
from collections.abc import Iterator

import structlog

from chat.importer import format_side_effects
from chat.tabular import (
    IMPORT_TARGETS,
    TABULAR_CONTENT_TYPES,
    detect_target,
    digest_document,
    map_columns,
    target_terms,
)

from .base import SSEEvent, Workflow, WorkflowContext

logger = structlog.get_logger(__name__)

# A target is auto-selected when it recognizes enough columns and clearly
# beats the runner-up; otherwise the user is asked.
_MIN_TARGET_SCORE = 0.4
_MIN_TARGET_MARGIN = 0.15

_CANCEL_WORDS = {"cancel", "stop", "abort", "annuler", "annule", "abandonner"}

_NEW_CONTAINER_WORDS = {"new", "nouvelle", "nouveau", "créer", "creer"}

_MAX_NARRATED_MAPPINGS = 15


def _words(message: str) -> set[str]:
    return set(re.findall(r"\w+", message.casefold(), re.UNICODE))


def is_cancel(message: str) -> bool:
    return bool(_words(message) & _CANCEL_WORDS)


def should_resume(state: dict | None, message: str) -> bool:
    """A staged import only intercepts turns that answer it — otherwise an
    unrelated question would re-enter the workflow instead of being answered."""
    if not state or state.get("workflow") != "import_document":
        return False
    if state.get("step") in (
        "awaiting_target",
        "awaiting_container",
        "awaiting_matrix",
    ):
        return True
    return is_cancel(message)


class ImportDocumentWorkflow(Workflow):
    name = "import_document"
    description = (
        "Digest a spreadsheet (xlsx/csv) the user attached to the chat and "
        "prepare importing its rows as objects: applied controls, pentest or "
        "audit findings, assets, risk scenarios of a risk assessment… Use this "
        "when the user uploads a file and wants its content imported, created, "
        "or updated. Works in any language."
    )

    def run(self, ctx: WorkflowContext) -> Iterator[SSEEvent]:
        tabular_docs = [
            d for d in ctx.documents if d.content_type in TABULAR_CONTENT_TYPES
        ]
        if tabular_docs:
            yield from self._digest_turn(ctx, tabular_docs[0])
            return

        state = self._load_state(ctx)
        if not state:
            yield self._token(
                "Attach an .xlsx or .csv file to your message and I'll help "
                "you import its content."
            )
            return

        if is_cancel(ctx.user_message):
            self._clear_state(ctx)
            yield self._token("Import cancelled. The file was not imported.")
            return

        if state.get("step") == "awaiting_target":
            yield from self._target_reply_turn(ctx, state)
            return

        if state.get("step") == "awaiting_container":
            yield from self._container_reply_turn(ctx, state)
            return

        if state.get("step") == "awaiting_matrix":
            yield from self._matrix_reply_turn(ctx, state)
            return

        if state.get("step") == "import_review":
            yield self._token(
                "Your import is still waiting for confirmation — use the card "
                "above, or say cancel to drop it."
            )
            return

        yield from self._narrate_mapping(ctx, state["data"])

    # ── Turn handlers ────────────────────────────────────────────────

    def _digest_turn(self, ctx: WorkflowContext, doc) -> Iterator[SSEEvent]:
        yield self._thinking(f"Reading {doc.filename}...")

        digest = digest_document(doc)
        if digest.error:
            self._clear_state(ctx)
            yield self._token(f"I couldn't digest **{doc.filename}**: {digest.error}")
            return

        # Header signature for the frontend's learned-mapping lookup.
        yield SSEEvent(
            type="mapping_request",
            content={
                "document_id": str(doc.id),
                "filename": digest.filename,
                "signature": digest.signature,
                "headers": digest.normalized_headers,
            },
        )

        data = {
            "document_id": str(doc.id),
            "filename": digest.filename,
            "signature": digest.signature,
            "headers": digest.headers,
            "normalized_headers": digest.normalized_headers,
            "row_count": digest.row_count,
            "row_count_capped": digest.row_count_capped,
        }

        rows = f"{digest.row_count}{'+' if digest.row_count_capped else ''}"
        columns = len([h for h in digest.normalized_headers if h])
        yield self._token(
            f"I read **{digest.filename}**: {rows} rows, {columns} columns.\n\n"
        )

        # The user's own words beat header statistics ("import these findings").
        stated_target = self._match_target_in_message(ctx.user_message)
        if stated_target:
            data["target"] = stated_target
            yield from self._proceed_to_mapping(ctx, data)
            return

        scores = detect_target(digest.normalized_headers)
        best_key, best_score = scores[0]
        runner_up_score = scores[1][1] if len(scores) > 1 else 0.0

        if best_score >= _MIN_TARGET_SCORE and (
            best_score - runner_up_score >= _MIN_TARGET_MARGIN
        ):
            data["target"] = best_key
            yield from self._proceed_to_mapping(ctx, data)
            return

        self._save_state(ctx, "awaiting_target", data)
        yield self._token("What should I import these rows as?")
        yield self._pending_choice(
            field="import_target",
            label="Import as",
            items=[
                {"id": key, "name": target["label"]}
                for key, target in IMPORT_TARGETS.items()
            ],
        )

    @staticmethod
    def _match_target_in_message(message: str) -> str | None:
        message = message.strip().lower()
        matches = [
            key
            for key in IMPORT_TARGETS
            if any(term in message for term in target_terms(key))
        ]
        # Only trust the message when it names exactly one target.
        return matches[0] if len(matches) == 1 else None

    def _target_reply_turn(
        self, ctx: WorkflowContext, state: dict
    ) -> Iterator[SSEEvent]:
        target_key = self._match_target_in_message(ctx.user_message)

        if not target_key:
            yield self._token("I didn't catch which object type you meant.")
            yield self._pending_choice(
                field="import_target",
                label="Import as",
                items=[
                    {"id": key, "name": target["label"]}
                    for key, target in IMPORT_TARGETS.items()
                ],
            )
            return

        data = {**state["data"], "target": target_key}
        yield from self._proceed_to_mapping(ctx, data)

    # ── Container selection (update an existing assessment) ─────────

    def _proceed_to_mapping(
        self, ctx: WorkflowContext, data: dict
    ) -> Iterator[SSEEvent]:
        """Ask whether to update an existing container before mapping."""
        container = IMPORT_TARGETS[data["target"]].get("container")
        if container and "container_id" not in data and ctx.request is not None:
            candidates = self._container_candidates(ctx, data["target"])
            if candidates:
                data["container_candidates"] = candidates
                self._save_state(ctx, "awaiting_container", data)
                yield self._token(
                    f"Should I update an existing {container['label']} or create "
                    "a new one?"
                )
                yield self._pending_choice(
                    field="import_container",
                    label="Import into",
                    items=self._container_items(container, candidates),
                )
                return
            data["container_id"] = None
        yield from self._after_container(ctx, data)

    @staticmethod
    def _container_items(container: dict, candidates: list[dict]) -> list[dict]:
        return [
            {"id": "__new__", "name": f"Create a new {container['label']}"}
        ] + candidates

    @staticmethod
    def _container_candidates(ctx: WorkflowContext, target_key: str) -> list[dict]:
        from iam.models import Folder, RoleAssignment

        from chat.tabular import container_model

        model = container_model(target_key)
        if model is None:
            return []

        change_ids = RoleAssignment.get_changeable_object_ids(ctx.request.user, model)
        return [
            {"id": str(row["id"]), "name": row["name"]}
            for row in model.objects.filter(id__in=change_ids)
            .order_by("-updated_at")
            .values("id", "name")[:10]
        ]

    @staticmethod
    def _match_candidate(message: str, candidates: list[dict]) -> dict | None:
        message = message.strip().casefold()
        return next(
            (c for c in candidates if c["name"].casefold() in message),
            None,
        )

    def _container_reply_turn(
        self, ctx: WorkflowContext, state: dict
    ) -> Iterator[SSEEvent]:
        data = state["data"]
        container = IMPORT_TARGETS[data["target"]].get("container") or {}
        candidates = data.get("container_candidates", [])

        # Names win over the "new" keyword: an assessment called "Renewal Q1"
        # contains "new".
        chosen = self._match_candidate(ctx.user_message, candidates)
        if chosen is None and _words(ctx.user_message) & _NEW_CONTAINER_WORDS:
            data = {**data, "container_id": None}
            yield from self._after_container(ctx, data)
            return

        if chosen is None:
            yield self._token("I didn't catch which assessment you meant.")
            yield self._pending_choice(
                field="import_container",
                label="Import into",
                items=self._container_items(container, candidates),
            )
            return

        data = {**data, "container_id": chosen["id"], "container_name": chosen["name"]}
        yield from self._after_container(ctx, data)

    # ── Risk matrix selection (only for a new risk assessment) ──────

    def _after_container(self, ctx: WorkflowContext, data: dict) -> Iterator[SSEEvent]:
        container = IMPORT_TARGETS[data["target"]].get("container") or {}
        needs_matrix = (
            container.get("needs_matrix")
            and not data.get("container_id")
            and not data.get("matrix_id")
            and ctx.request is not None
        )
        if not needs_matrix:
            yield from self._narrate_mapping(ctx, data)
            return

        matrices = self._matrix_candidates(ctx)
        if not matrices:
            self._clear_state(ctx)
            yield self._token(
                "I can't create a risk assessment: no risk matrix is available "
                "to you. Import a risk matrix library first, then attach the "
                "file again."
            )
            return

        if len(matrices) == 1:
            data = {
                **data,
                "matrix_id": matrices[0]["id"],
                "matrix_name": matrices[0]["name"],
            }
            yield from self._narrate_mapping(ctx, data)
            return

        data = {**data, "matrix_candidates": matrices}
        self._save_state(ctx, "awaiting_matrix", data)
        yield self._token("Which risk matrix should the new risk assessment use?")
        yield self._pending_choice(
            field="import_matrix", label="Risk matrix", items=matrices
        )

    @staticmethod
    def _matrix_candidates(ctx: WorkflowContext) -> list[dict]:
        from core.models import RiskMatrix
        from iam.models import Folder, RoleAssignment

        (view_ids, _, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), ctx.request.user, RiskMatrix
        )
        return [
            {"id": str(row["id"]), "name": row["name"]}
            for row in RiskMatrix.objects.filter(id__in=view_ids, is_enabled=True)
            .order_by("name")
            .values("id", "name")[:10]
        ]

    def _matrix_reply_turn(
        self, ctx: WorkflowContext, state: dict
    ) -> Iterator[SSEEvent]:
        data = state["data"]
        candidates = data.get("matrix_candidates", [])
        chosen = self._match_candidate(ctx.user_message, candidates)

        if chosen is None:
            yield self._token("I didn't catch which risk matrix you meant.")
            yield self._pending_choice(
                field="import_matrix", label="Risk matrix", items=candidates
            )
            return

        data = {**data, "matrix_id": chosen["id"], "matrix_name": chosen["name"]}
        yield from self._narrate_mapping(ctx, data)

    # ── Narration ────────────────────────────────────────────────────

    def _narrate_mapping(self, ctx: WorkflowContext, data: dict) -> Iterator[SSEEvent]:
        target_key = data["target"]
        target = IMPORT_TARGETS[target_key]
        mapped, unmapped = map_columns(data["normalized_headers"], target_key)
        data = {**data, "mapping": mapped, "unmapped": unmapped}

        lines = [
            f"This looks like **{target['label'].lower()}** — I recognize "
            f"{len(mapped)} of {len(mapped) + len(unmapped)} columns.\n"
        ]

        if mapped:
            pairs = [
                f"`{header}`" + (f" → `{field_name}`" if header != field_name else "")
                for header, field_name in list(mapped.items())[:_MAX_NARRATED_MAPPINGS]
            ]
            overflow = len(mapped) - _MAX_NARRATED_MAPPINGS
            if overflow > 0:
                pairs.append(f"+{overflow} more")
            lines.append(f"**Mapped automatically:** {', '.join(pairs)}\n")

        if unmapped:
            names = ", ".join(f"`{h}`" for h in unmapped)
            lines.append(f"**Not recognized (will be ignored):** {names}\n")

        yield self._token("\n".join(lines))
        yield from self._dry_run(ctx, data)

    # ── Dry-run + confirmation ───────────────────────────────────────

    def _dry_run(self, ctx: WorkflowContext, data: dict) -> Iterator[SSEEvent]:
        from rest_framework.exceptions import PermissionDenied

        from chat.importer import run_import
        from chat.models import IndexedDocument

        target = IMPORT_TARGETS[data["target"]]
        doc = IndexedDocument.objects.filter(id=data["document_id"]).first()
        if doc is None:
            self._clear_state(ctx)
            yield self._token(
                "\nThe uploaded file is no longer available — please attach it again."
            )
            return

        # The apply reuses this folder: find_existing() is folder-scoped, so a
        # different folder at confirm time would invalidate these counts.
        data = {**data, "folder_id": str(doc.folder_id)}

        yield self._thinking("Dry-running the import (nothing is written)...")
        try:
            report = run_import(
                ctx.request,
                doc,
                data["mapping"],
                data["target"],
                folder_id=data["folder_id"],
                dry_run=True,
                target_id=data.get("container_id"),
                matrix_id=data.get("matrix_id"),
            )
        except PermissionDenied:
            self._clear_state(ctx)
            yield self._token(
                f"\nYou don't have permission to import {target['label'].lower()} "
                "into this domain."
            )
            return
        except Exception:
            logger.error(
                "chat_import_dry_run_failed",
                document_id=data["document_id"],
                exc_info=True,
            )
            self._save_state(ctx, "mapping_review", data)
            yield self._token(
                "\nI couldn't dry-run this import. You can adjust the file and "
                "attach it again."
            )
            return

        self._save_state(ctx, "import_review", data)

        summary = (
            f"\nDry-run on {report['row_count']} rows: "
            f"**{report['created']} would be created**, "
            f"**{report['updated']} updated**"
        )
        if report["skipped"]:
            summary += f", {report['skipped']} skipped"
        if report["failed"]:
            summary += f", {report['failed']} invalid"
        summary += "."
        side_effects = format_side_effects(report.get("details"))
        if side_effects:
            summary += (
                f"\n\nObjects referenced by name that don't exist yet and would "
                f"be created alongside: {side_effects}."
            )
        if report["errors"]:
            summary += "\n\nSample issues:\n" + "\n".join(
                f"- {e}" for e in report["errors"]
            )
        if report["truncated"]:
            summary += (
                f"\n\n⚠️ Only the first {report['row_count']} rows are covered — "
                "split the file to import the rest."
            )
        summary += "\n\nNothing has been written yet — confirm below to import."
        yield self._token(summary)

        from iam.models import Folder

        container_name = (
            data.get("container_name") if data.get("container_id") else None
        )
        yield self._pending_action(
            {
                "action": "import",
                "display_name": target["label"],
                "document_id": data["document_id"],
                "row_count": report["row_count"],
                "created": report["created"],
                "updated": report["updated"],
                "skipped": report["skipped"],
                "failed": report["failed"],
                "truncated": report["truncated"],
                "target_name": container_name,
                "folder_id": data["folder_id"],
                "folder_name": ""
                if container_name
                else (
                    Folder.objects.filter(id=data["folder_id"])
                    .values_list("name", flat=True)
                    .first()
                    or ""
                ),
                "available_folders": [],
                "items": [],
            }
        )
