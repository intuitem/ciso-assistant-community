"""
EBIOS RM Assist workflow.

Context: User is on an EBIOS RM study page and wants help conducting
the study. Creates objects across workshops 1-3 based on the study
context and user input.

Steps:
    1. Read study state — what exists, what's missing (deterministic)
    2. If no framing context available, ask targeted questions (conversational)
    3. Generate assets, feared events, RoTo couples, strategic scenarios,
       attack paths, and operational scenarios via LLM (reasoning + creation)
    4. Present summary of what was created (deterministic)
"""

import structlog
from typing import Iterator

from django.apps import apps

from iam.models import Folder
from ..page_context import ParsedContext
from .base import Workflow, WorkflowContext, SSEEvent

logger = structlog.get_logger(__name__)

# Validation schemas for LLM-generated objects
ASSET_SCHEMA = {
    "required": ["name"],
    "types": {"name": str, "description": str, "type": str},
}
FEARED_EVENT_SCHEMA = {
    "required": ["name", "description"],
    "types": {"name": str, "description": str, "asset_names": list},
}
ROTO_SCHEMA = {
    "required": ["risk_origin", "target_objective"],
    "types": {"motivation": int, "resources": int, "activity": int},
}
STRATEGIC_SCENARIO_SCHEMA = {
    "required": ["name", "roto_index"],
    "types": {"name": str, "description": str, "roto_index": int},
}
ATTACK_PATH_SCHEMA = {
    "required": ["name", "scenario_index"],
    "types": {"name": str, "description": str, "scenario_index": int},
}


class EbiosRMAssistWorkflow(Workflow):
    name = "ebios_rm_assist"
    description = (
        "Help conduct an EBIOS RM study. Creates assets, feared events, "
        "risk origin / target objective couples, strategic scenarios, attack paths, "
        "and operational scenarios based on the study context. Use this when the "
        "user asks to help with the EBIOS RM study, conduct the analysis, "
        "fill in the workshops, or get started. Works in any language. "
        "Can also be triggered from a domain/folder page to create a full study "
        "from scratch using existing domain assets."
    )
    context_models = []  # Available on ALL pages (folder, study, or general)

    def run(self, ctx: WorkflowContext) -> Iterator[SSEEvent]:
        # Check for a saved checkpoint first
        state = self._load_state(ctx)
        if state:
            step = state.get("step", "")
            data = state.get("data", {})
            if step == "awaiting_domain":
                yield from self._resume_domain_choice(ctx)
                return
            if step == "awaiting_matrix":
                yield from self._resume_matrix_choice(ctx, data)
                return
            if step == "awaiting_framing":
                yield from self._resume_framing(ctx, data)
                return

        # No checkpoint — route based on page context
        model_key = ctx.parsed_context.model_key if ctx.parsed_context else None
        if model_key == "folder":
            yield from self._run_from_folder(ctx)
        elif model_key == "ebios_rm_study":
            yield from self._run_from_study(ctx)
        else:
            yield from self._run_from_general(ctx)

    # ── Resume from checkpoints ──────────────────────────────────────

    def _resume_domain_choice(self, ctx) -> Iterator[SSEEvent]:
        folders = list(
            Folder.objects.filter(
                id__in=ctx.accessible_folder_ids,
                content_type=Folder.ContentType.DOMAIN,
            )
        )
        picked = self._match_choice(ctx.user_message, folders)
        if not picked:
            self._clear_state(ctx)
            yield self._token("I didn't recognize that domain. Please try again.")
            return
        ctx.parsed_context = ParsedContext(
            model_key="folder", object_id=str(picked.id), page_type="detail"
        )
        self._clear_state(ctx)
        yield from self._run_from_folder(ctx)

    def _resume_matrix_choice(self, ctx, data) -> Iterator[SSEEvent]:
        RiskMatrix = apps.get_model("core", "RiskMatrix")
        matrices = list(RiskMatrix.objects.filter(is_enabled=True))
        picked = self._match_choice(ctx.user_message, matrices)
        if not picked:
            self._clear_state(ctx)
            yield self._token("I didn't recognize that matrix. Please try again.")
            return
        ctx.parsed_context = ParsedContext(
            model_key="folder", object_id=data.get("folder_id"), page_type="detail"
        )
        self._clear_state(ctx)
        yield from self._run_from_folder(ctx, forced_matrix=picked)

    def _resume_framing(self, ctx, data) -> Iterator[SSEEvent]:
        RiskMatrix = apps.get_model("core", "RiskMatrix")
        matrix = RiskMatrix.objects.filter(id=data.get("risk_matrix_id")).first()
        ctx.parsed_context = ParsedContext(
            model_key="folder", object_id=data.get("folder_id"), page_type="detail"
        )
        self._clear_state(ctx)
        yield from self._run_from_folder(ctx, forced_matrix=matrix)

    def _match_choice(self, user_message: str, options: list):
        msg = user_message.strip().lower()
        for option in options:
            if msg == (getattr(option, "name", "") or str(option)).lower():
                return option
        return None

    # ── Entry point: from a general page ─────────────────────────────

    def _run_from_general(self, ctx: WorkflowContext) -> Iterator[SSEEvent]:
        folders = list(
            Folder.objects.filter(
                id__in=ctx.accessible_folder_ids,
                content_type=Folder.ContentType.DOMAIN,
            ).order_by("name")[:20]
        )
        if not folders:
            yield self._token("No domains are available. Please create a domain first.")
            return
        if len(folders) == 1:
            ctx.parsed_context = ParsedContext(
                model_key="folder", object_id=str(folders[0].id), page_type="detail"
            )
            yield from self._run_from_folder(ctx)
            return

        # Multiple domains — save checkpoint and ask
        self._save_state(ctx, "awaiting_domain", {})
        yield self._token(
            "I can help you conduct an EBIOS RM study. "
            "Which domain should the study be created in?"
        )
        yield self._pending_choice(
            field="domain",
            label="Select a domain",
            items=[
                {"id": str(f.id), "name": f.name, "description": f.description or ""}
                for f in folders
            ],
        )

    # ── Entry point: from a folder/domain page ───────────────────────

    def _run_from_folder(
        self, ctx: WorkflowContext, forced_matrix=None
    ) -> Iterator[SSEEvent]:
        """Drive a full EBIOS RM study from a domain page."""

        yield self._thinking("Looking up domain and existing assets...")

        folder_id = ctx.parsed_context.object_id
        if str(folder_id) not in ctx.accessible_folder_ids:
            yield self._token("You don't have access to this domain.")
            return
        try:
            folder = Folder.objects.get(id=folder_id)
        except Folder.DoesNotExist:
            yield self._token("I couldn't find this domain.")
            return

        # Check for existing assets in this domain
        Asset = apps.get_model("core", "Asset")
        domain_assets = list(
            Asset.objects.filter(
                folder_id=folder_id,
            ).values("id", "name", "type", "description")[:30]
        )

        # Resolve risk matrix
        risk_matrix = forced_matrix
        if not risk_matrix:
            RiskMatrix = apps.get_model("core", "RiskMatrix")
            available_matrices = list(
                RiskMatrix.objects.filter(
                    is_enabled=True,
                    folder_id__in=ctx.accessible_folder_ids,
                ).order_by("name")[:20]
            )
            if not available_matrices:
                available_matrices = list(
                    RiskMatrix.objects.filter(is_enabled=True).order_by("name")[:20]
                )
            if not available_matrices:
                yield self._token(
                    "No risk matrix is available. Please load a risk matrix "
                    "library first before creating an EBIOS RM study."
                )
                return
            if len(available_matrices) == 1:
                risk_matrix = available_matrices[0]
            else:
                # Save checkpoint and ask
                self._save_state(ctx, "awaiting_matrix", {"folder_id": str(folder_id)})
                yield self._token(
                    f"I'll create an EBIOS RM study for **{folder.name}**. "
                    f"First, which risk matrix should I use?"
                )
                yield self._pending_choice(
                    field="risk_matrix",
                    label="Select a risk matrix",
                    items=[
                        {"id": str(m.id), "name": m.name} for m in available_matrices
                    ],
                )
                return

        yield self._thinking(
            f"Domain: {folder.name}\n"
            f"Assets found: {len(domain_assets)}\n"
            f"Risk matrix: {risk_matrix.name}"
        )

        # If no assets and no framing context, ask for input
        if not domain_assets and not self._has_framing_context(
            {"description": "", "name": folder.name}, ctx
        ):
            self._save_state(
                ctx,
                "awaiting_framing",
                {"folder_id": str(folder_id), "risk_matrix_id": str(risk_matrix.id)},
            )
            yield self._token(
                f"I'll create an EBIOS RM study for the domain **{folder.name}**.\n\n"
                f"I found no existing assets in this domain. "
                f"To generate a relevant study, I need some context:\n\n"
                f"1. **What is the scope** of this study? "
                f"(e.g., patient data management, e-commerce platform)\n"
                f"2. **What are the critical assets/systems** involved?\n"
                f"3. **What sector/industry** are you in?\n"
                f"4. **Who are the main third parties** involved?\n\n"
                f"A few sentences are enough — I'll generate the full study."
            )
            return

        # Create the EBIOS RM study
        yield self._thinking("Creating EBIOS RM study...")
        EbiosRMStudy = apps.get_model("ebios_rm", "EbiosRMStudy")

        # Build a study name from context
        study_name = self._generate_study_name(ctx, folder.name)

        study_obj = EbiosRMStudy.objects.create(
            name=study_name,
            description=ctx.user_message,
            folder=folder,
            risk_matrix=risk_matrix,
        )

        # Navigate the user to the new study page for better context
        yield self._navigate(f"/ebios-rm/{study_obj.id}")

        study = {
            "id": str(study_obj.id),
            "name": study_obj.name,
            "description": study_obj.description or "",
            "folder_id": str(study_obj.folder_id),
            "risk_matrix_id": str(study_obj.risk_matrix_id),
            "obj": study_obj,
        }

        yield self._thinking(f"Created study: {study_name}")

        # Link existing domain assets to the study
        created = {
            "assets": [],
            "feared_events": [],
            "rotos": [],
            "strategic_scenarios": [],
            "attack_paths": [],
            "operational_scenarios": [],
        }

        if domain_assets:
            for a in domain_assets:
                study_obj.assets.add(a["id"])
            created["assets"] = [
                {"id": str(a["id"]), "name": a["name"]} for a in domain_assets
            ]
            yield self._thinking(
                f"Linked {len(domain_assets)} existing assets to the study."
            )
        else:
            # Generate assets if none exist
            yield self._thinking("Workshop 1: Generating assets...")
            assets = self._generate_assets(ctx, study)
            if assets:
                created["assets"] = self._create_assets(study, assets)
                yield self._thinking(f"Created {len(created['assets'])} assets.")

        # Now run W1 (feared events) through W4 using the standard pipeline
        yield from self._run_workshops(ctx, study, created, start_from="feared_events")

    def _generate_study_name(self, ctx: WorkflowContext, folder_name: str) -> str:
        """Generate a concise study name from context."""
        prompt = (
            f"Generate a concise EBIOS RM study name (max 60 chars) for this context:\n"
            f"Domain: {folder_name}\n"
            f"User request: {ctx.user_message}\n\n"
            f"Return ONLY the study name, nothing else. "
            f"Use the same language as the user request."
        )
        name = self._call_llm(ctx, prompt).strip().strip("\"'")
        return name[:100] if name else f"EBIOS RM — {folder_name}"

    # ── Entry point: from an existing study page ─────────────────────

    def _run_from_study(self, ctx: WorkflowContext) -> Iterator[SSEEvent]:
        """Original flow: assist an existing EBIOS RM study."""
        yield self._thinking("Reading study state...")

        study = self._fetch_study(ctx)
        if not study:
            yield self._token(
                "I couldn't find the EBIOS RM study. "
                "Please make sure you're on a study page."
            )
            return

        state = self._get_study_state(study)
        yield self._thinking(
            f"Study: {study['name']}\n"
            f"Assets: {state['asset_count']}, "
            f"Feared events: {state['feared_event_count']}, "
            f"RoTo couples: {state['roto_count']}, "
            f"Strategic scenarios: {state['strategic_scenario_count']}, "
            f"Attack paths: {state['attack_path_count']}, "
            f"Operational scenarios: {state['operational_scenario_count']}"
        )

        # Check if we have enough context to generate
        has_framing = self._has_framing_context(study, ctx)
        if not has_framing:
            yield from self._ask_framing_questions(study)
            return

        # Generate objects for missing workshops
        created = {
            "assets": [],
            "feared_events": [],
            "rotos": [],
            "strategic_scenarios": [],
            "attack_paths": [],
            "operational_scenarios": [],
        }

        # W1: Assets
        if state["asset_count"] == 0:
            yield self._thinking("Workshop 1: Generating assets...")
            assets = self._generate_assets(ctx, study)
            if assets:
                created["assets"] = self._create_assets(study, assets)
                yield self._thinking(f"Created {len(created['assets'])} assets.")

        # Run remaining workshops
        start = "feared_events" if state["feared_event_count"] == 0 else None
        if start is None and state["roto_count"] == 0:
            start = "rotos"
        if start is None and state["strategic_scenario_count"] == 0:
            start = "strategic_scenarios"
        if start is None and state["attack_path_count"] == 0:
            start = "attack_paths"
        if start is None and state["operational_scenario_count"] == 0:
            start = "operational_scenarios"

        if start:
            yield from self._run_workshops(ctx, study, created, start_from=start)
        else:
            yield from self._stream_summary(ctx, study, created)

    # ── Shared workshop pipeline ─────────────────────────────────────

    def _run_workshops(
        self,
        ctx: WorkflowContext,
        study: dict,
        created: dict,
        start_from: str = "feared_events",
    ) -> Iterator[SSEEvent]:
        """Run workshops from a given starting point through W4."""
        steps = [
            "feared_events",
            "rotos",
            "strategic_scenarios",
            "attack_paths",
            "operational_scenarios",
        ]
        start_idx = steps.index(start_from) if start_from in steps else 0

        all_assets = self._get_all_assets(study)

        # W1: Feared events
        if start_idx <= 0:
            all_feared_events = self._get_all_feared_events(study)
            if not all_feared_events and all_assets:
                yield self._thinking("Workshop 1: Generating feared events...")
                feared_events = self._generate_feared_events(ctx, study, all_assets)
                if feared_events:
                    created["feared_events"] = self._create_feared_events(
                        study, feared_events, all_assets
                    )
                    yield self._thinking(
                        f"Created {len(created['feared_events'])} feared events."
                    )
                else:
                    yield self._token(
                        "I couldn't generate feared events. "
                        "Please provide more detail about the scope and try again."
                    )
                    return

        all_feared_events = self._get_all_feared_events(study)

        # W2: RoTo couples
        if start_idx <= 1:
            all_rotos = self._get_all_rotos(study)
            if not all_rotos and all_feared_events:
                yield self._thinking(
                    "Workshop 2: Generating risk origin / target objective couples..."
                )
                rotos = self._generate_rotos(ctx, study, all_feared_events)
                if rotos:
                    created["rotos"] = self._create_rotos(
                        study, rotos, all_feared_events
                    )
                    yield self._thinking(
                        f"Created {len(created['rotos'])} RoTo couples."
                    )
                else:
                    yield self._token(
                        "I couldn't generate RoTo couples. The LLM may be unavailable."
                    )

        all_rotos = self._get_all_rotos(study)

        # W3: Strategic scenarios
        if start_idx <= 2:
            all_strategic_scenarios = self._get_all_strategic_scenarios(study)
            if not all_strategic_scenarios and all_rotos:
                yield self._thinking("Workshop 3: Generating strategic scenarios...")
                scenarios = self._generate_strategic_scenarios(
                    ctx, study, all_rotos, all_feared_events
                )
                if scenarios:
                    created["strategic_scenarios"] = self._create_strategic_scenarios(
                        study, scenarios, all_rotos, all_feared_events
                    )
                    yield self._thinking(
                        f"Created {len(created['strategic_scenarios'])} strategic scenarios."
                    )
                else:
                    yield self._token(
                        "I couldn't generate strategic scenarios. The LLM may be unavailable."
                    )

        all_strategic_scenarios = self._get_all_strategic_scenarios(study)

        # W3: Attack paths
        if start_idx <= 3:
            all_attack_paths = self._get_all_attack_paths(study)
            if not all_attack_paths and all_strategic_scenarios:
                yield self._thinking("Workshop 3: Generating attack paths...")
                attack_paths = self._generate_attack_paths(
                    ctx, study, all_strategic_scenarios
                )
                if attack_paths:
                    created["attack_paths"] = self._create_attack_paths(
                        study, attack_paths, all_strategic_scenarios
                    )
                    yield self._thinking(
                        f"Created {len(created['attack_paths'])} attack paths."
                    )
                else:
                    yield self._token(
                        "I couldn't generate attack paths. The LLM may be unavailable."
                    )

        all_attack_paths = self._get_all_attack_paths(study)

        # W4: Operational scenarios
        if start_idx <= 4:
            existing_ops = (
                apps.get_model("ebios_rm", "OperationalScenario")
                .objects.filter(ebios_rm_study=study["obj"])
                .exists()
            )
            if not existing_ops and all_attack_paths:
                yield self._thinking("Workshop 4: Generating operational scenarios...")
                created["operational_scenarios"] = self._create_operational_scenarios(
                    study, all_attack_paths
                )
                yield self._thinking(
                    f"Created {len(created['operational_scenarios'])} operational scenarios."
                )

        # Summary
        yield from self._stream_summary(ctx, study, created)

    # ── Framing ──────────────────────────────────────────────────────

    def _has_framing_context(self, study: dict, ctx: WorkflowContext) -> bool:
        """Check if we have enough context to generate a draft."""
        # Study description is the primary framing source
        if study.get("description") and len(study["description"]) > 30:
            return True
        # Check conversation history for framing answers
        if ctx.history:
            history_text = " ".join(
                m.get("content", "") for m in ctx.history if m.get("role") == "user"
            )
            # If user has provided substantial context in conversation
            if len(history_text) > 50:
                return True
        return False

    def _ask_framing_questions(self, study: dict) -> Iterator[SSEEvent]:
        """Ask the user for context needed to generate the draft."""
        yield self._token(
            f"To draft the EBIOS RM study **{study['name']}**, "
            f"I need some context about your organization and scope. "
            f"Please describe:\n\n"
            f"1. **What is the scope** of this study? "
            f"(e.g., patient data management system, e-commerce platform, "
            f"industrial control network)\n"
            f"2. **What are the critical assets/systems** involved? "
            f"(e.g., databases, web applications, employee workstations, "
            f"medical devices)\n"
            f"3. **What sector/industry** are you in? "
            f"(e.g., healthcare, finance, manufacturing, government)\n"
            f"4. **Who are the main third parties** involved? "
            f"(e.g., cloud providers, maintenance contractors, software vendors)\n\n"
            f"You can answer in any language. "
            f"A few sentences are enough — I'll generate a complete draft "
            f"that you can then refine in each workshop."
        )

    # ── Study data fetching ──────────────────────────────────────────

    def _fetch_study(self, ctx: WorkflowContext) -> dict | None:
        try:
            EbiosRMStudy = apps.get_model("ebios_rm", "EbiosRMStudy")
            study = (
                EbiosRMStudy.objects.select_related("risk_matrix", "folder")
                .filter(
                    id=ctx.parsed_context.object_id,
                    folder_id__in=ctx.accessible_folder_ids,
                )
                .first()
            )
            if not study:
                return None
            return {
                "id": str(study.id),
                "name": study.name,
                "description": study.description or "",
                "folder_id": str(study.folder_id),
                "risk_matrix_id": str(study.risk_matrix_id)
                if study.risk_matrix_id
                else None,
                "obj": study,
            }
        except Exception as e:
            logger.error("Failed to fetch EBIOS RM study: %s", e)
            return None

    def _get_study_state(self, study: dict) -> dict:
        """Count existing objects for each workshop step."""
        study_obj = study["obj"]
        FearedEvent = apps.get_model("ebios_rm", "FearedEvent")
        RoTo = apps.get_model("ebios_rm", "RoTo")
        StrategicScenario = apps.get_model("ebios_rm", "StrategicScenario")
        AttackPath = apps.get_model("ebios_rm", "AttackPath")
        OperationalScenario = apps.get_model("ebios_rm", "OperationalScenario")

        return {
            "asset_count": study_obj.assets.count(),
            "feared_event_count": FearedEvent.objects.filter(
                ebios_rm_study=study_obj
            ).count(),
            "roto_count": RoTo.objects.filter(ebios_rm_study=study_obj).count(),
            "strategic_scenario_count": StrategicScenario.objects.filter(
                ebios_rm_study=study_obj
            ).count(),
            "attack_path_count": AttackPath.objects.filter(
                ebios_rm_study=study_obj
            ).count(),
            "operational_scenario_count": OperationalScenario.objects.filter(
                ebios_rm_study=study_obj
            ).count(),
        }

    # ── Asset generation (W1) ───────────────────────────────────────

    def _generate_assets(self, ctx: WorkflowContext, study: dict) -> list[dict]:
        """Ask LLM to generate assets based on study context."""
        prompt = (
            f"You are an EBIOS RM expert. Based on the study context below, "
            f"generate a list of assets (both primary business assets and "
            f"supporting technical assets) relevant to this study.\n\n"
            f"**Study:** {study['name']}\n"
            f"**Description:** {study['description']}\n\n"
            f"Return ONLY a JSON array. Each item must have:\n"
            f'- "name": string (concise asset name)\n'
            f'- "description": string (brief description)\n'
            f'- "type": "PR" for primary (business process, data) or '
            f'"SP" for supporting (server, application, network)\n\n'
            f"Generate 5-10 assets covering the main business processes "
            f"and their supporting infrastructure. "
            f"Return ONLY the JSON array, no other text.\n\n"
            f"Example:\n"
            f'[{{"name": "Patient records", "description": "Electronic health records database", "type": "PR"}}]'
        )
        return self._generate_validated(ctx, prompt, ASSET_SCHEMA)

    def _create_assets(self, study: dict, assets: list[dict]) -> list[dict]:
        """Create Asset objects and link them to the study."""
        Asset = apps.get_model("core", "Asset")
        study_obj = study["obj"]
        created = []
        for a in assets:
            try:
                asset = Asset.objects.create(
                    name=a["name"],
                    description=a.get("description", ""),
                    type=a.get("type", "SP"),
                    folder_id=study["folder_id"],
                )
                study_obj.assets.add(asset)
                created.append({"id": str(asset.id), "name": asset.name})
            except Exception as e:
                logger.warning("Failed to create asset %s: %s", a.get("name"), e)
        return created

    def _get_all_assets(self, study: dict) -> list[dict]:
        study_obj = study["obj"]
        return [
            {"id": str(a.id), "name": a.name, "type": a.type}
            for a in study_obj.assets.all()
        ]

    # ── Feared event generation (W1) ────────────────────────────────

    def _generate_feared_events(
        self, ctx: WorkflowContext, study: dict, assets: list[dict]
    ) -> list[dict]:
        asset_lines = "\n".join(f"- {a['name']} ({a['type']})" for a in assets)
        prompt = (
            f"You are an EBIOS RM expert. Based on the study scope and assets below, "
            f"generate feared events (dreaded scenarios of harm to the organization).\n\n"
            f"**Study:** {study['name']}\n"
            f"**Description:** {study['description']}\n\n"
            f"**Assets:**\n{asset_lines}\n\n"
            f"Return ONLY a JSON array. Each item must have:\n"
            f'- "name": string (concise feared event name)\n'
            f'- "description": string (what could happen and its impact)\n'
            f'- "asset_names": list of asset names affected (from the list above)\n\n'
            f"Generate 3-6 feared events covering the main risks "
            f"(confidentiality breach, availability loss, integrity compromise, etc.). "
            f"Return ONLY the JSON array, no other text."
        )
        return self._generate_validated(ctx, prompt, FEARED_EVENT_SCHEMA)

    def _create_feared_events(
        self, study: dict, feared_events: list[dict], assets: list[dict]
    ) -> list[dict]:
        FearedEvent = apps.get_model("ebios_rm", "FearedEvent")
        Terminology = apps.get_model("core", "Terminology")
        study_obj = study["obj"]
        asset_map = {a["name"].lower(): a["id"] for a in assets}

        # Get qualifications for linking
        qualifications = {
            t.name: t
            for t in Terminology.objects.filter(
                field_path=Terminology.FieldPath.QUALIFICATIONS, is_visible=True
            )
        }

        created = []
        for fe in feared_events:
            try:
                obj = FearedEvent.objects.create(
                    name=fe["name"],
                    description=fe.get("description", ""),
                    ebios_rm_study=study_obj,
                )
                # Link assets
                for aname in fe.get("asset_names", []):
                    aid = asset_map.get(aname.lower())
                    if aid:
                        obj.assets.add(aid)
                # Auto-detect qualifications from description
                desc_lower = (fe.get("description", "") + " " + fe["name"]).lower()
                for qual_name, qual_obj in qualifications.items():
                    if qual_name in desc_lower:
                        obj.qualifications.add(qual_obj)
                created.append({"id": str(obj.id), "name": obj.name})
            except Exception as e:
                logger.warning(
                    "Failed to create feared event %s: %s", fe.get("name"), e
                )
        return created

    def _get_all_feared_events(self, study: dict) -> list[dict]:
        FearedEvent = apps.get_model("ebios_rm", "FearedEvent")
        return [
            {"id": str(fe.id), "name": fe.name}
            for fe in FearedEvent.objects.filter(ebios_rm_study=study["obj"])
        ]

    # ── RoTo generation (W2) ────────────────────────────────────────

    def _generate_rotos(
        self, ctx: WorkflowContext, study: dict, feared_events: list[dict]
    ) -> list[dict]:
        Terminology = apps.get_model("core", "Terminology")
        risk_origins = list(
            Terminology.objects.filter(
                field_path=Terminology.FieldPath.ROTO_RISK_ORIGIN, is_visible=True
            ).values_list("name", flat=True)
        )
        risk_origin_list = ", ".join(risk_origins)
        fe_lines = "\n".join(f"- {fe['name']}" for fe in feared_events)

        prompt = (
            f"You are an EBIOS RM expert. Generate Risk Origin / Target Objective "
            f"(RO/TO) couples for this study.\n\n"
            f"**Study:** {study['name']}\n"
            f"**Description:** {study['description']}\n\n"
            f"**Feared events:**\n{fe_lines}\n\n"
            f"**Available risk origins:** {risk_origin_list}\n\n"
            f"Return ONLY a JSON array. Each item must have:\n"
            f'- "risk_origin": string (one of the available risk origins above)\n'
            f'- "target_objective": string (what the attacker wants to achieve)\n'
            f'- "motivation": integer 1-4 (1=very_low, 2=low, 3=significant, 4=strong)\n'
            f'- "resources": integer 1-4 (1=limited, 2=significant, 3=important, 4=unlimited)\n'
            f'- "activity": integer 1-4 (1=very_low, 2=low, 3=moderate, 4=important)\n'
            f'- "feared_event_names": list of feared event names this RoTo targets\n\n'
            f"Generate 3-5 relevant RoTo couples with realistic profiles. "
            f"Return ONLY the JSON array, no other text."
        )
        return self._generate_validated(ctx, prompt, ROTO_SCHEMA)

    def _create_rotos(
        self, study: dict, rotos: list[dict], feared_events: list[dict]
    ) -> list[dict]:
        RoTo = apps.get_model("ebios_rm", "RoTo")
        Terminology = apps.get_model("core", "Terminology")
        study_obj = study["obj"]
        fe_map = {fe["name"].lower(): fe["id"] for fe in feared_events}

        # Build risk origin terminology lookup
        ro_terms = {
            t.name.lower(): t
            for t in Terminology.objects.filter(
                field_path=Terminology.FieldPath.ROTO_RISK_ORIGIN, is_visible=True
            )
        }

        created = []
        for roto in rotos:
            try:
                ro_name = roto.get("risk_origin", "").lower()
                ro_term = ro_terms.get(ro_name)
                if not ro_term:
                    # Try partial match
                    for key, term in ro_terms.items():
                        if ro_name in key or key in ro_name:
                            ro_term = term
                            break
                if not ro_term:
                    logger.warning("Unknown risk origin: %s", roto.get("risk_origin"))
                    continue

                obj = RoTo.objects.create(
                    ebios_rm_study=study_obj,
                    risk_origin=ro_term,
                    target_objective=roto.get("target_objective", ""),
                    motivation=roto.get("motivation", 0),
                    resources=roto.get("resources", 0),
                    activity=roto.get("activity", 0),
                    is_selected=True,
                )
                # Link feared events
                for fe_name in roto.get("feared_event_names", []):
                    fe_id = fe_map.get(fe_name.lower())
                    if fe_id:
                        obj.feared_events.add(fe_id)
                created.append({"id": str(obj.id), "name": str(obj)})
            except Exception as e:
                logger.warning("Failed to create RoTo: %s", e)
        return created

    def _get_all_rotos(self, study: dict) -> list[dict]:
        RoTo = apps.get_model("ebios_rm", "RoTo")
        return [
            {"id": str(r.id), "name": str(r)}
            for r in RoTo.objects.filter(ebios_rm_study=study["obj"])
        ]

    # ── Strategic scenario generation (W3) ──────────────────────────

    def _generate_strategic_scenarios(
        self,
        ctx: WorkflowContext,
        study: dict,
        rotos: list[dict],
        feared_events: list[dict],
    ) -> list[dict]:
        roto_lines = "\n".join(f"- [{i + 1}] {r['name']}" for i, r in enumerate(rotos))
        fe_lines = "\n".join(f"- {fe['name']}" for fe in feared_events)

        prompt = (
            f"You are an EBIOS RM expert. Generate strategic scenarios "
            f"that describe high-level attack storylines.\n\n"
            f"**Study:** {study['name']}\n"
            f"**Description:** {study['description']}\n\n"
            f"**RoTo couples:**\n{roto_lines}\n\n"
            f"**Feared events:**\n{fe_lines}\n\n"
            f"Return ONLY a JSON array. Each item must have:\n"
            f'- "name": string (concise scenario name)\n'
            f'- "description": string (narrative of the strategic attack scenario)\n'
            f'- "roto_index": integer (1-based index from the RoTo list above)\n\n'
            f"Generate one strategic scenario per RoTo couple. "
            f"Return ONLY the JSON array, no other text."
        )
        return self._generate_validated(ctx, prompt, STRATEGIC_SCENARIO_SCHEMA)

    def _create_strategic_scenarios(
        self,
        study: dict,
        scenarios: list[dict],
        rotos: list[dict],
        feared_events: list[dict],
    ) -> list[dict]:
        StrategicScenario = apps.get_model("ebios_rm", "StrategicScenario")
        study_obj = study["obj"]

        created = []
        for sc in scenarios:
            try:
                idx = sc.get("roto_index", 0) - 1
                if idx < 0 or idx >= len(rotos):
                    continue
                roto_id = rotos[idx]["id"]

                obj = StrategicScenario.objects.create(
                    name=sc["name"],
                    description=sc.get("description", ""),
                    ebios_rm_study=study_obj,
                    ro_to_couple_id=roto_id,
                )
                created.append({"id": str(obj.id), "name": obj.name})
            except Exception as e:
                logger.warning("Failed to create strategic scenario: %s", e)
        return created

    def _get_all_strategic_scenarios(self, study: dict) -> list[dict]:
        StrategicScenario = apps.get_model("ebios_rm", "StrategicScenario")
        return [
            {"id": str(s.id), "name": s.name}
            for s in StrategicScenario.objects.filter(ebios_rm_study=study["obj"])
        ]

    # ── Attack path generation (W3) ─────────────────────────────────

    def _generate_attack_paths(
        self,
        ctx: WorkflowContext,
        study: dict,
        strategic_scenarios: list[dict],
    ) -> list[dict]:
        sc_lines = "\n".join(
            f"- [{i + 1}] {s['name']}" for i, s in enumerate(strategic_scenarios)
        )
        prompt = (
            f"You are an EBIOS RM expert. Generate attack paths that describe "
            f"how each strategic scenario could be carried out.\n\n"
            f"**Study:** {study['name']}\n"
            f"**Description:** {study['description']}\n\n"
            f"**Strategic scenarios:**\n{sc_lines}\n\n"
            f"Return ONLY a JSON array. Each item must have:\n"
            f'- "name": string (concise attack path name)\n'
            f'- "description": string (how the attack progresses through the ecosystem)\n'
            f'- "scenario_index": integer (1-based index from the strategic scenario list)\n\n'
            f"Generate 1-2 attack paths per strategic scenario. "
            f"Return ONLY the JSON array, no other text."
        )
        return self._generate_validated(ctx, prompt, ATTACK_PATH_SCHEMA)

    def _create_attack_paths(
        self,
        study: dict,
        attack_paths: list[dict],
        strategic_scenarios: list[dict],
    ) -> list[dict]:
        AttackPath = apps.get_model("ebios_rm", "AttackPath")
        study_obj = study["obj"]

        created = []
        for ap in attack_paths:
            try:
                idx = ap.get("scenario_index", 0) - 1
                if idx < 0 or idx >= len(strategic_scenarios):
                    continue
                sc_id = strategic_scenarios[idx]["id"]

                obj = AttackPath.objects.create(
                    name=ap["name"],
                    description=ap.get("description", ""),
                    strategic_scenario_id=sc_id,
                    ebios_rm_study=study_obj,
                    is_selected=True,
                )
                created.append({"id": str(obj.id), "name": obj.name})
            except Exception as e:
                logger.warning("Failed to create attack path: %s", e)
        return created

    def _get_all_attack_paths(self, study: dict) -> list[dict]:
        AttackPath = apps.get_model("ebios_rm", "AttackPath")
        return [
            {"id": str(ap.id), "name": ap.name}
            for ap in AttackPath.objects.filter(ebios_rm_study=study["obj"])
        ]

    # ── Operational scenario generation (W4/W5) ─────────────────────

    def _create_operational_scenarios(
        self, study: dict, attack_paths: list[dict]
    ) -> list[dict]:
        """Create one operational scenario per selected attack path (deterministic)."""
        OperationalScenario = apps.get_model("ebios_rm", "OperationalScenario")
        study_obj = study["obj"]

        created = []
        for ap in attack_paths:
            try:
                # Check if one already exists for this attack path
                if OperationalScenario.objects.filter(attack_path_id=ap["id"]).exists():
                    continue
                obj = OperationalScenario.objects.create(
                    ebios_rm_study=study_obj,
                    attack_path_id=ap["id"],
                    is_selected=True,
                )
                created.append({"id": str(obj.id), "name": str(obj)})
            except Exception as e:
                logger.warning("Failed to create operational scenario: %s", e)
        return created

    # ── Summary ──────────────────────────────────────────────────────

    def _stream_summary(
        self,
        ctx: WorkflowContext,
        study: dict,
        created: dict,
    ) -> Iterator[SSEEvent]:
        """Stream a summary of what was created, then an LLM commentary."""
        total = sum(len(v) for v in created.values())
        if total == 0:
            yield self._token(
                "The study already has content in all workshops. "
                "Navigate to individual workshops to refine the analysis, "
                "or ask me about specific aspects you'd like to improve."
            )
            return

        # Build a summary prompt for the LLM
        summary_parts = []
        labels = {
            "assets": "Assets (W1)",
            "feared_events": "Feared Events (W1)",
            "rotos": "RoTo Couples (W2)",
            "strategic_scenarios": "Strategic Scenarios (W3)",
            "attack_paths": "Attack Paths (W3)",
            "operational_scenarios": "Operational Scenarios (W4)",
        }
        for key, label in labels.items():
            items = created[key]
            if items:
                names = ", ".join(i["name"] for i in items)
                summary_parts.append(f"- **{label}**: {len(items)} created ({names})")

        summary_text = "\n".join(summary_parts)

        prompt = (
            f"You just helped draft an EBIOS RM study. Here's what was created:\n\n"
            f"**Study:** {study['name']}\n\n"
            f"**Created objects:**\n{summary_text}\n\n"
            f"Provide a brief summary of the draft and suggest what the user "
            f"should review or refine in each workshop. Be concise and actionable. "
            f"Mention that they can navigate to each workshop to adjust the results."
        )
        yield from self._stream_llm(ctx, prompt)
        self._clear_state(ctx)

    # ── Helpers ──────────────────────────────────────────────────────

    def _read_choice_from_history(
        self, ctx: WorkflowContext, field: str, options: list
    ):
        """
        Check if the user has already answered a pending_choice by looking at
        the last user message in history. Match it against the option names.
        """
        if not ctx.history:
            return None
        # The last user message should be the choice (sent by selectChoice)
        last_user = None
        for msg in reversed(ctx.history):
            if msg.get("role") == "user":
                last_user = msg.get("content", "").strip()
                break
        if not last_user:
            return None
        # Match against option names (case-insensitive)
        for option in options:
            name = getattr(option, "name", "") or str(option)
            if last_user.lower() == name.lower():
                return option
        return None
