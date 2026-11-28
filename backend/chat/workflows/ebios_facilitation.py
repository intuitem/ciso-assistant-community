"""
Facilitation mode of the EBIOS RM assistant.

The study's own data says which step comes next (not the chat memory), so a session can stop and resume,
and a partly filled study is completed where it is incomplete. Each step goes: ask one question (the model
writes it from the step's goal and what the study already holds) → propose objects built only from the
user's answers and existing data → write them once the user agrees. Every write checks the user's
permissions on the study's folder; every read goes through the user's ReadScope.
"""

import json
import re
from contextvars import ContextVar
from typing import Iterator

import structlog
from django.apps import apps

from .base import SSEEvent, WorkflowContext

logger = structlog.get_logger(__name__)

STEPS = (
    (
        "framing",
        1,
        "the scope and objectives of the study (what is studied, why, by when)",
    ),
    ("assets", 1, "the business values (primary assets) and their supporting assets"),
    ("feared_events", 1, "the feared events on the business values"),
    (
        "gravity",
        1,
        "the gravity of each feared event on the study's scale, and whether a feared event is missing",
    ),
    (
        "baseline",
        1,
        "the security baseline: the frameworks and rules that apply, and the known gaps",
    ),
    ("rotos", 2, "the risk sources, their target objectives, motivation and resources"),
    (
        "stakeholders",
        3,
        "the ecosystem's stakeholders (providers, partners) and their dependency, penetration, maturity and trust",
    ),
    (
        "strategic_scenarios",
        3,
        "the strategic scenarios: which risk source reaches which feared event, through which stakeholders",
    ),
    (
        "operational_scenarios",
        4,
        "how each attack path is carried out technically, and its likelihood",
    ),
    ("risk_assessment", 5, "the risk assessment built from the operational scenarios"),
    (
        "treatment",
        5,
        "the treatment of each risk: strategy (mitigate, accept, avoid, transfer), security measures "
        "and residual likelihood",
    ),
)
WRITE_PERMS = {
    "framing": ("change_ebiosrmstudy",),
    "assets": ("change_ebiosrmstudy",),
    "feared_events": ("add_fearedevent", "change_fearedevent"),
    "gravity": ("change_fearedevent",),
    "baseline": ("change_ebiosrmstudy",),
    "rotos": ("add_roto", "change_roto"),
    "stakeholders": ("add_stakeholder", "change_stakeholder"),
    "strategic_scenarios": (
        "add_strategicscenario",
        "change_strategicscenario",
        "add_attackpath",
        "change_attackpath",
    ),
    "operational_scenarios": ("add_operationalscenario", "change_operationalscenario"),
    "risk_assessment": ("add_riskassessment",),
    "treatment": ("change_riskscenario", "add_appliedcontrol"),
}
ITEM_FORMATS = {
    "framing": '{"objectives": "...", "scope": "what is in and out", "constraints": "deadline, budget..."} (one item)',
    "assets": '{"name": "...", "type": "PR" for a business value (a process or information the '
    'organisation needs) or "SP" for a supporting asset (a system, application, network, provider), '
    '"supports": ["business values this supporting asset serves", only when the user said so]}. '
    "Reuse a domain asset's exact name when the user means it; name new business values as the user does",
    "feared_events": '{"name": "...", "description": "...", "assets": ["business value names"], '
    '"gravity": "the level as written in the scale, only if the user gave it"}',
    "gravity": '{"feared_event": "name", "gravity": "the level as written in the scale (e.g. its code)", '
    '"new": true only for a feared event the user names that the study does not hold yet}',
    "baseline": '{"frameworks": ["frameworks or rules named by the user"], "gaps": ["known gaps"]} (one item)',
    "rotos": '{"risk_origin": "one of the risk origins listed", "target_objective": "...", '
    '"motivation", "resources", "activity": 1-4 only when the user rated them, "feared_events": ["names"]}',
    "stakeholders": '{"entity": "organisation name", "category": "one of the categories listed", '
    '"dependency": 0-4, "penetration": 0-4, "maturity": 1-4, "trust": 1-4}',
    "strategic_scenarios": '{"name": "...", "description": "...", "roto": number of the couple listed, '
    '"feared_event": "exact name", "attack_paths": [{"name": "...", "stakeholders": ["entity names"]}]}',
    "operational_scenarios": '{"attack_path": "exact name", "description": "how it is carried out", '
    '"likelihood": "the level as written in the scale (e.g. its code)"}',
    "risk_assessment": '{"name": "..."} (one item)',
    "treatment": '{"risk_scenario": "exact name", "treatment": "mitigate", "accept", "avoid" or "transfer", '
    '"measures": ["security measures: the user\'s, or a few concrete ones if the user asked you to suggest"], '
    '"residual_likelihood": "the level as written in the scale, only if the user gave it"}',
}

REQUIRED = {
    "framing": ("objectives",),
    "assets": ("name",),
    "feared_events": ("name",),
    "gravity": ("feared_event", "gravity"),
    "baseline": (),
    "rotos": ("risk_origin", "target_objective"),
    "stakeholders": ("entity", "category"),
    "strategic_scenarios": ("name",),
    "operational_scenarios": ("attack_path",),
    "risk_assessment": ("name",),
    "treatment": ("risk_scenario", "treatment"),
}
EXISTING = {
    "assets": "core.Asset",
    "feared_events": "ebios_rm.FearedEvent",
    "gravity": "ebios_rm.FearedEvent",
    "strategic_scenarios": "ebios_rm.StrategicScenario",
}
# Ratings a model tends to fill in on its own, and the words that show the user gave them
# (criterion names; level codes and names come from the study's matrix, see _level_words).
RATINGS = {
    "feared_events": {"gravity": ("gravity", "gravité", "severity")},
    "gravity": {"gravity": ("gravity", "gravité", "severity")},
    "rotos": {
        "motivation": ("motivation", "motivé", "motivated"),
        "resources": ("resources", "ressources", "moyens", "means"),
        "activity": ("activity", "activité", "actif", "active"),
    },
    "stakeholders": {
        "dependency": ("dependency", "dépendance", "dépend"),
        "penetration": ("penetration", "pénétration"),
        "maturity": ("maturity", "maturité"),
        "trust": ("trust", "confiance"),
    },
    "operational_scenarios": {
        "likelihood": ("likelihood", "vraisemblance", "likely", "probab")
    },
    "treatment": {
        "residual_likelihood": ("residual", "résiduel", "vraisemblance", "likelihood")
    },
}
RISK_ORIGINS = {  # the interface's own French names for the built-in risk origins
    "fr": {
        "activist": "activiste",
        "amateur": "amateur",
        "avenger": "vengeur",
        "competitor": "concurrent",
        "organized_crime": "crime organisé",
        "other": "autre",
        "pathological": "pathologique",
        "state": "État",
        "terrorist": "terroriste",
    }
}
PATHLESS = {
    "fr": "Ces scénarios stratégiques n'ont pas encore de **chemin d'attaque** : {scenarios}. "
    "Par quelles parties prenantes l'attaquant passerait-il pour chacun ?",
    "en": "These strategic scenarios have no **attack path** yet: {scenarios}. Through which "
    "stakeholders would the attacker go for each?",
}
REWRITE = {
    "fr": "Écrivez le cadrage complet tel que vous voulez l'enregistrer (objectif, périmètre, échéance).",
    "en": "Write the full framing as you want it recorded (objective, scope, deadline).",
}
BUTTONS = {
    "en": {"record": "Record", "change": "Change", "skip": "Skip this step"},
    "fr": {"record": "Enregistrer", "change": "Modifier", "skip": "Passer cette étape"},
}
DONE = {
    "fr": {
        "complete": "Les ateliers 1 à 5 sont renseignés pour cette étude : les mesures sont dans "
        "l'analyse de risques, à suivre dans le plan d'action. Vous pouvez revoir chaque atelier "
        "dans les pages de l'étude.",
        "skipped": "J'ai parcouru les ateliers 1 à 5, mais ces étapes ont été passées : {steps}. "
        "Dites-moi si vous voulez y revenir.",
    },
    "en": {
        "complete": "Workshops 1 to 5 are filled in for this study: the measures are in the risk "
        "assessment, to follow up in the action plan. You can review each workshop in the study "
        "pages.",
        "skipped": "I went through workshops 1 to 5, but these steps were skipped: {steps}. Tell me "
        "if you want to go back to them.",
    },
}
QUESTIONS = {
    "fr": {
        "framing": "Commençons par le cadrage de l'étude **{study}**. Quel est son objectif, son "
        "périmètre (ce qui est inclus et exclu) et son échéance ?",
        "assets": "Quelles sont les **valeurs métier** du périmètre, c'est-à-dire les processus ou "
        "informations essentiels à l'organisation ? Le domaine contient déjà ces biens, que je "
        "peux reprendre comme biens supports : {domain_assets}. Lesquels soutiennent quelles "
        "valeurs métier ?",
        "feared_events": "Pour chaque valeur métier ({business_values}), quels **événements "
        "redoutés** craignez-vous (indisponibilité, fuite, altération…) et avec quelle gravité "
        "({gravity_scale}) ?",
        "gravity": "Ces événements redoutés n'ont pas encore de **gravité** : {unrated}. Quelle "
        "gravité pour chacun ({gravity_scale}) ? Manque-t-il un événement redouté ?",
        "baseline": "Quel est votre **socle de sécurité** : les référentiels ou règles qui "
        "s'appliquent (par exemple le guide d'hygiène de l'ANSSI) et les écarts connus ?",
        "rotos": "Atelier 2 : quelles **sources de risque** retenez-vous, avec leur objectif visé, "
        "et, si vous les connaissez, leur motivation et leurs ressources (de 1 à 4) ? Sources "
        "possibles : {origins}.",
        "stakeholders": "Atelier 3 : quelles **parties prenantes** de l'écosystème retenez-vous "
        "parmi les tiers connus ({entities}), avec leur catégorie et leur dépendance, pénétration, "
        "maturité et confiance (de 1 à 4) ?",
        "strategic_scenarios": "Pour chaque couple source de risque / objectif visé ({rotos}), "
        "quel **scénario stratégique** : par quelles parties prenantes l'attaquant passerait-il, "
        "et quel événement redouté atteindrait-il ?",
        "operational_scenarios": "Atelier 4 : pour chaque chemin d'attaque ({paths}), comment "
        "l'attaque se déroulerait-elle techniquement, et avec quelle **vraisemblance** "
        "({likelihood_scale}) ?",
        "risk_assessment": "Atelier 5 : je peux générer l'**analyse de risques** de l'étude à "
        "partir de ses {operational_count} scénarios opérationnels retenus, comme le bouton « Générer "
        "l'analyse de risques » de la page de l'étude.",
        "treatment": "Atelier 5 : pour chaque risque ({open_risks}), quelle **stratégie de "
        "traitement** (réduire, accepter, éviter, transférer), quelles **mesures de sécurité**, et "
        "quelle vraisemblance résiduelle visée ({likelihood_scale}) ? Je peux aussi vous suggérer "
        "des mesures.",
    },
    "en": {
        "framing": "Let's start with the framing of the study **{study}**. What is its objective, "
        "its scope (what is in and out) and its deadline?",
        "assets": "What are the **business values** in scope, the processes or information the "
        "organisation needs? The domain already holds these assets, which I can reuse as "
        "supporting assets: {domain_assets}. Which of them support which business values?",
        "feared_events": "For each business value ({business_values}), which **feared events** "
        "worry you (unavailability, leak, alteration…), and how severe ({gravity_scale})?",
        "gravity": "These feared events have no **gravity** yet: {unrated}. What gravity for each "
        "({gravity_scale})? Is a feared event missing?",
        "baseline": "What is your **security baseline**: the frameworks or rules that apply (for "
        "example a hygiene guide) and the known gaps?",
        "rotos": "Workshop 2: which **risk sources** do you keep, with their target objective and, "
        "if you know them, their motivation and resources (1 to 4)? Possible sources: {origins}.",
        "stakeholders": "Workshop 3: which **stakeholders** of the ecosystem do you keep among the "
        "known third parties ({entities}), with their category and their dependency, penetration, "
        "maturity and trust (1 to 4)?",
        "strategic_scenarios": "For each risk source / target objective couple ({rotos}), which "
        "**strategic scenario**: through which stakeholders would the attacker go, and which "
        "feared event would they reach?",
        "operational_scenarios": "Workshop 4: for each attack path ({paths}), how would the attack "
        "unfold technically, and how **likely** is it ({likelihood_scale})?",
        "risk_assessment": "Workshop 5: I can generate the study's **risk assessment** from its "
        "{operational_count} selected operational scenarios, like the \u201cGenerate the risk "
        "assessment\u201d button on the study page.",
        "treatment": "Workshop 5: for each risk ({open_risks}), which **treatment strategy** "
        "(mitigate, accept, avoid, transfer), which **security measures**, and which target "
        "residual likelihood ({likelihood_scale})? I can also suggest measures.",
    },
}
LABELS = {
    "en": {
        "objectives": "objectives",
        "constraints": "constraints",
        "type": "type",
        "PR": "business value",
        "SP": "supporting asset",
        "description": "description",
        "assets": "assets",
        "gravity": "gravity",
        "frameworks": "frameworks",
        "gaps": "gaps",
        "risk_origin": "risk origin",
        "target_objective": "target objective",
        "motivation": "motivation",
        "resources": "resources",
        "activity": "activity",
        "feared_events": "feared events",
        "category": "category",
        "dependency": "dependency",
        "penetration": "penetration",
        "maturity": "maturity",
        "trust": "trust",
        "roto": "couple",
        "attack_paths": "attack paths",
        "stakeholders": "stakeholders",
        "supports": "supports",
        "likelihood": "likelihood",
        "treatment": "treatment",
        "measures": "measures",
        "residual_likelihood": "residual likelihood",
        "mitigate": "mitigate",
        "accept": "accept",
        "avoid": "avoid",
        "transfer": "transfer",
        "new": "new",
        "existing": "already in the tool, reused or updated",
    },
    "fr": {
        "objectives": "objectifs",
        "constraints": "contraintes",
        "type": "type",
        "PR": "valeur métier",
        "SP": "bien support",
        "description": "description",
        "assets": "biens",
        "gravity": "gravité",
        "frameworks": "référentiels",
        "gaps": "écarts",
        "risk_origin": "source de risque",
        "target_objective": "objectif visé",
        "motivation": "motivation",
        "resources": "ressources",
        "activity": "activité",
        "feared_events": "événements redoutés",
        "category": "catégorie",
        "dependency": "dépendance",
        "penetration": "pénétration",
        "maturity": "maturité",
        "trust": "confiance",
        "roto": "couple",
        "attack_paths": "chemins d'attaque",
        "stakeholders": "parties prenantes",
        "supports": "au service de",
        "likelihood": "vraisemblance",
        "treatment": "traitement",
        "measures": "mesures",
        "residual_likelihood": "vraisemblance résiduelle",
        "mitigate": "réduire",
        "accept": "accepter",
        "avoid": "éviter",
        "transfer": "transférer",
        "new": "nouveau",
        "existing": "déjà dans l'outil, réutilisé ou mis à jour",
    },
}

INTENT = """You help run an EBIOS RM study inside a GRC tool. The assistant's last message:
<assistant>{last}</assistant>
The user now writes:
<user>{message}</user>
Rule: if the message asks for any change, addition or correction, the intent is "amend", even when it also
says to record. "accept" is only a plain agreement with nothing to change.
What does the user do? Reply with JSON only: {{"intent": one of
"answer" (gives information the assistant asked for),
"accept" (agrees to record the proposal shown, as it is, with no change requested),
"amend" (wants the proposal changed, even if they agree with part of it),
"reject" (refuses the proposal or says not to record it, with nothing to change),
"skip" (wants to move to the next step),
"draft" (asks you to draft all the remaining workshops at once),
"question" (asks something about the method or the study),
"stop" (wants to stop or pause),
"step": the step the user's message is about, one of {steps}, or null}}"""

PROPOSE = """You help a practitioner run an EBIOS RM study (workshop {workshop}) in a GRC tool. Current step:
{goal}.

What the study already holds:
{state}
{extra}
The user's latest message:
<user>{message}</user>

Using ONLY what the user said (latest message and conversation) and what the study already holds (never invent names,
providers, numbers or ratings the user did not give), build the items to record for this step.
Item format: {fmt}
If the user's answers are not enough to build the items, reply {{"ask": "one short question"}} instead.
{feedback}Reply with JSON only: {{"items": [...]}} or {{"ask": "..."}}"""

ASK = """You are facilitating an EBIOS RM study (workshop {workshop}) with a practitioner, inside a GRC tool.
The next step is: {goal}.

What the study already holds:
{state}
{extra}
You are talking with the practitioner: reply to them directly (no preamble, no draft, no quotes), briefly,
as an experienced EBIOS RM facilitator. Ask, do not propose: never list candidate items, ratings or
providers of your own (the practitioner knows their organisation; at most one short example as a hint).
First one sentence on what the
study already holds for this step and what is missing, then the one or two questions you need. Give the
scale exactly as listed when a rating is needed, never ask again for what is already recorded, and do not
answer for the user. The practitioner just wrote: {message}"""


def _parse_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text or "", re.S)
    try:
        return json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        return {}


def _lang(ctx, table: dict) -> str:
    return ctx.user_lang[:2] if ctx.user_lang[:2] in table else "en"


def _refresh_scope(ctx) -> None:
    """ReadScope caches readable ids for the request; objects created since are not in them."""
    from chat.scoping import ReadScope

    if isinstance(ctx.scope, ReadScope):
        ctx.scope = ReadScope(ctx.scope.user)


# when the current proposal started recording: objects it created match by exact name only
_BATCH_START = ContextVar("ebios_batch_start", default=None)


def _find(by_name: dict, name):
    """The object of that name, or of a near spelling (a model paraphrases names it was given)."""
    import difflib

    wanted = _norm(name)
    if not wanted:
        return None
    if wanted in by_name:
        return by_name[wanted]
    start = _BATCH_START.get()
    # two items of one proposal with near names ("A → X", "B → X") are two objects, not one
    by_name = {
        k: o
        for k, o in by_name.items()
        if start is None or (getattr(o, "created_at", None) or start) < start
    }
    close = difflib.get_close_matches(wanted, list(by_name), n=1, cutoff=0.8)
    if close:
        return by_name[close[0]]
    # a compound name given by its first part ("<strategic>" for "<strategic> - <path>"), if unique
    heads = [k for k in by_name if k.startswith(wanted + " - ")]
    return by_name[heads[0]] if len(heads) == 1 else None


def _mentions(text: str, token: str) -> bool:
    """`token` in `text` at a word start ("fort" in "forte", "g4" in "(g4)", not "v1" in "v12")."""
    if not token:
        return False
    if re.search(r"\d$", token):
        return re.search(rf"(?<![\w]){re.escape(token)}(?!\d)", text) is not None
    return re.search(rf"(?<![\w]){re.escape(token)}", text) is not None


def _norm(text) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


class EbiosFacilitationMixin:
    """Mixed into EbiosRMAssistWorkflow: needs _token, _thinking, _call_llm, _stream_llm, state helpers."""

    def _facilitate(self, ctx: WorkflowContext, study_obj) -> Iterator[SSEEvent]:
        from .ebios_rm_assist import _can_write

        state = self._load_state(ctx) or {}
        data = state.get("data", {}) if state.get("step") == "facilitate" else {}
        if data.get("study_id") != str(study_obj.id):
            data = {"study_id": str(study_obj.id), "skipped": []}
        step = self._next_step(ctx, study_obj, data.get("skipped", []))
        last = ""
        if ctx.history and ctx.history[-1].get("role") == "assistant":
            last = ctx.history[-1].get("content", "")

        # A click on the proposal's buttons is an answer we do not need a model to read.
        clicked = next(
            (
                key
                for buttons in BUTTONS.values()
                for key, name in buttons.items()
                if _norm(ctx.user_message) == _norm(name)
            ),
            None,
        )
        if data.get("phase") == "proposed" and clicked == "change":
            data["awaiting_change"] = True
            self._save_state(ctx, "facilitate", data)
            if (
                data.get("proposal_step") == "framing"
            ):  # recorded as written: ask for the full text
                yield SSEEvent(type="token", content=REWRITE[_lang(ctx, REWRITE)])
            else:
                yield self._token("What should I change?")
            return
        if clicked == "skip":
            intent = "skip"
        elif data.get("phase") == "proposed" and clicked == "record":
            intent = "accept"
        elif data.get("phase"):
            verdict = _parse_json(
                self._call_llm(
                    ctx,
                    INTENT.format(
                        last=last[-1500:],
                        message=ctx.user_message,
                        steps=", ".join(f'"{k}" ({g})' for k, _, g in STEPS),
                    ),
                )
            )
            intent = verdict.get("intent") or "answer"
            # Free text records only when it is a plain short agreement, never right after
            # "change": anything longer gets a fresh proposal to confirm (one click more at worst).
            if intent == "accept" and (
                data.pop("awaiting_change", False) or len(ctx.user_message.split()) > 8
            ):
                intent = "amend"
            # The user may come back to an earlier step (a missing feared event, the baseline...)
            if verdict.get("step") in ("risk_assessment", "treatment") and intent in (
                "answer",
                "amend",
                "start",
            ):
                # workshop 5: the first of its steps the study still needs
                data["skipped"] = [
                    k
                    for k in data.get("skipped", [])
                    if k not in ("risk_assessment", "treatment")
                ]
                for key in ("phase", "proposal", "proposal_step", "focus"):
                    data.pop(key, None)
                intent = "start"
            elif data.get("phase") == "finished" and verdict.get("step") in WRITE_PERMS:
                # Going back to a step after the end: ask its question again
                data["skipped"] = [
                    k for k in data.get("skipped", []) if k != verdict["step"]
                ]
                data.pop("phase", None)
                data["focus"] = verdict["step"]
                intent = "start" if intent != "question" else intent
            elif verdict.get("step") in WRITE_PERMS and intent in ("answer", "amend"):
                if verdict["step"] != data.get("proposal_step"):
                    data.pop("proposal", None)
                data["focus"] = verdict["step"]
        else:
            intent = "start"
        logger.info(
            "ebios_facilitation", step=step, phase=data.get("phase"), intent=intent
        )

        if intent == "stop":
            self._clear_state(ctx)
            yield self._token(
                "Paused. Ask me to continue the EBIOS RM study whenever you want: "
                "I will resume from where the study stands."
            )
            return
        if intent == "question":
            summary, _ = self._study_snapshot(ctx, study_obj, step or "framing")
            yield from self._stream_llm(
                ctx,
                f"What the study holds in the tool:\n{summary}\n\n"
                f"Answer the practitioner's question about EBIOS RM or their study, briefly; for "
                f"what is recorded, rely on the study above.\n"
                f"Question: {ctx.user_message}\n\nThen, in one sentence, invite them to continue with "
                f"the current step: {dict((s, g) for s, _, g in STEPS).get(step, 'the treatment')}.",
            )
            return
        if intent == "draft":
            from .ebios_rm_assist import WORKSHOP_ADD_PERMS

            if not _can_write(
                ctx.scope.user,
                study_obj.folder,
                ("change_ebiosrmstudy", *WORKSHOP_ADD_PERMS),
            ):
                yield self._token(
                    "You don't have permission to draft the workshops of this study."
                )
                return
            self._clear_state(ctx)
            yield from self._draft_remaining(ctx, study_obj)
            return
        if intent == "reject" and data.get("phase") == "proposed":
            # Dropped, not rebuilt: the user moves on from the current state of the study.
            for key in ("phase", "proposal", "proposal_step", "focus"):
                data.pop(key, None)
            step = self._next_step(ctx, study_obj, data.get("skipped", []))
            intent = "start"
        if intent == "skip" and step:
            # Leaving a step the user came back to returns to the study's next step;
            # otherwise the next step itself is skipped.
            if not data.pop("focus", None):
                data["skipped"] = [*data.get("skipped", []), step]
            for key in ("phase", "proposal", "proposal_step"):
                data.pop(key, None)
            step = self._next_step(ctx, study_obj, data["skipped"])

        recorded_step = data.get("proposal_step") or step
        if data.get("phase") == "proposed" and intent == "accept" and recorded_step:
            if not _can_write(
                ctx.scope.user, study_obj.folder, WRITE_PERMS[recorded_step]
            ):
                yield self._token(
                    "You don't have permission to record this step in this study."
                )
                data["skipped"] = [*data.get("skipped", []), recorded_step]
            else:
                done = self._apply(
                    ctx, study_obj, recorded_step, data.get("proposal", [])
                )
                yield self._thinking(f"Recorded: {done}")
                yield SSEEvent(type="token", content=f"{done}.\n\n")
            for key in ("phase", "proposal", "proposal_step", "focus"):
                data.pop(key, None)
            _refresh_scope(ctx)  # what was just recorded counts for the next step
            step = self._next_step(ctx, study_obj, data.get("skipped", []))
            intent = "start"
        step = data.get("focus") or step

        if not step:
            # Stays attached to the study: "back to the stakeholders" resumes it, never a new study.
            data["phase"] = "finished"
            self._save_state(ctx, "facilitate", data)
            lang = ctx.user_lang[:2] if ctx.user_lang[:2] in DONE else "en"
            skipped = [NOUNS[lang][k] for k in data.get("skipped", [])]
            text = (
                DONE[lang]["skipped"].format(steps=", ".join(skipped))
                if skipped
                else DONE[lang]["complete"]
            )
            yield SSEEvent(type="token", content=text)
            return

        if step == "stakeholders" and not self._stakeholders_possible(ctx, study_obj):
            data["skipped"] = [*data.get("skipped", []), step]
            self._save_state(ctx, "facilitate", data)
            yield self._token(
                "The ecosystem's third parties are not in the tool yet and you may not create "
                "them: ask an administrator to add them, then come back to the stakeholders. "
                "Let's continue with the strategic scenarios.\n\n"
            )
            step = self._next_step(ctx, study_obj, data["skipped"])
            if not step:
                return
        workshop = dict((s, w) for s, w, _ in STEPS)[step]
        goal = dict((s, g) for s, _, g in STEPS)[step]
        summary, extra = self._study_snapshot(ctx, study_obj, step)

        if step == "risk_assessment" and intent in ("start", "skip"):
            # nothing to extract from the user: propose right away, the buttons decide
            noun = NOUNS[_lang(ctx, NOUNS)]["risk_assessment"]
            items = [{"name": f"{study_obj.name} — {noun}"}]
            data.update(phase="proposed", proposal=items, proposal_step=step)
            self._save_state(ctx, "facilitate", data)
            yield from self._ask(ctx, study_obj, step, buttons=False)
            yield from self._render_proposal(ctx, step, items, study_obj)
            return
        if intent == "start" or data.get("phase") is None and intent in ("skip",):
            data["phase"] = "asked"
            self._save_state(ctx, "facilitate", data)
            yield self._thinking(f"Workshop {workshop}: {goal}")
            yield from self._ask(ctx, study_obj, step)
            return

        # The user answered the question, amended or rejected the proposal: build (or rebuild) it.
        feedback = ""
        if data.get("phase") == "proposed":
            feedback = (
                f"Your previous proposal was {json.dumps(data.get('proposal'), ensure_ascii=False)}; "
                f"the user replied: {ctx.user_message!r}. Take it into account.\n"
            )
        if step == "framing":
            # Free text needs no extraction: the user's own words, so nothing is invented
            reply = {"items": [{"objectives": ctx.user_message.strip()}]}
        else:
            reply = _parse_json(
                self._call_llm(
                    ctx,
                    PROPOSE.format(
                        message=ctx.user_message,
                        workshop=workshop,
                        goal=goal,
                        state=summary,
                        extra=extra,
                        fmt=ITEM_FORMATS[step],
                        feedback=feedback,
                    ),
                )
            )
        # Only items shaped for this step: a model answering another step is not recorded here.
        items = [
            i
            for i in reply.get("items", [])
            if isinstance(i, dict)
            and all(i.get(k) not in (None, "", []) for k in REQUIRED[step])
            and (step != "baseline" or i.get("frameworks") or i.get("gaps"))
        ]
        items = self._drop_unstated_ratings(ctx, study_obj, step, items)
        if not items:
            data["phase"] = "asked"
            self._save_state(ctx, "facilitate", data)
            yield self._token("I need a little more to propose something. ")
            yield from self._ask(ctx, study_obj, step)
            return
        data.update(phase="proposed", proposal=items, proposal_step=step)
        self._save_state(ctx, "facilitate", data)
        yield from self._render_proposal(ctx, step, items, study_obj)

    def _ask(self, ctx, study, step: str, buttons: bool = True) -> Iterator[SSEEvent]:
        """The step's question, written once per language and filled from the study's data:
        method-correct and the same with any model. Other languages get the English one translated."""
        lang = ctx.user_lang[:2] if ctx.user_lang[:2] in QUESTIONS else "en"
        fes = self._scoped(ctx, "ebios_rm.FearedEvent").filter(ebios_rm_study=study)
        rotos = self._scoped(ctx, "ebios_rm.RoTo").filter(ebios_rm_study=study)
        none = "—"
        values = {
            "study": study.name,
            "domain_assets": ", ".join(
                self._scoped(ctx, "core.Asset")
                .filter(folder=study.folder)
                .values_list("name", flat=True)[:30]
            )
            or none,
            "business_values": ", ".join(
                self._study_assets(ctx, study)
                .filter(type="PR")
                .values_list("name", flat=True)
            )
            or none,
            "unrated": ", ".join(
                fes.filter(gravity__lt=0).values_list("name", flat=True)
            )
            or none,
            "gravity_scale": ", ".join(self._scale(study, "impact")),
            "likelihood_scale": ", ".join(self._scale(study, "probability")),
            "origins": ", ".join(
                RISK_ORIGINS.get(lang, {}).get(o, o.replace("_", " "))
                for o in self._terms("ROTO_RISK_ORIGIN")
            ),
            "entities": ", ".join(
                e.name
                for e in self._scoped(ctx, "tprm.Entity").exclude(builtin=True)[:30]
            )
            or none,
            "rotos": "; ".join(_roto_label(r, lang) for r in rotos) or none,
            "paths": ", ".join(
                self._scoped(ctx, "ebios_rm.AttackPath")
                .filter(ebios_rm_study=study, is_selected=True)
                .values_list("name", flat=True)
            )
            or none,
        }
        scenarios = self._scoped(ctx, "core.RiskScenario").filter(
            risk_assessment__ebios_rm_study=study
        )
        values["operational_count"] = (
            self._scoped(ctx, "ebios_rm.OperationalScenario")
            .filter(ebios_rm_study=study, is_selected=True)
            .count()
        )
        values["open_risks"] = (
            "; ".join(r.name for r in scenarios.filter(treatment="open")[:20]) or none
        )
        text = QUESTIONS[lang][step].format(**values)
        pathless = self._pathless(ctx, study) if step == "strategic_scenarios" else []
        if pathless:
            text = PATHLESS[lang].format(scenarios=", ".join(pathless))
        # French and English are written natively; another language is translated as fixed text.
        yield (
            SSEEvent(type="token", content=text)
            if lang == ctx.user_lang[:2]
            else self._token(text)
        )
        if not buttons:
            yield SSEEvent(type="token", content="\n\n")
            return
        buttons = BUTTONS.get(ctx.user_lang[:2], BUTTONS["en"])
        yield self._pending_choice(
            field="ebios_step",
            label="Or move on:",
            items=[{"id": "skip", "name": buttons["skip"]}],
        )

    # ── Study state, from the data and through the user's scope ──────

    def _scoped(self, ctx, model_label: str):
        return ctx.scope.queryset(apps.get_model(*model_label.split(".")))

    def _next_step(self, ctx, study, skipped) -> str | None:
        fe = self._scoped(ctx, "ebios_rm.FearedEvent").filter(ebios_rm_study=study)
        aps = self._scoped(ctx, "ebios_rm.AttackPath").filter(
            ebios_rm_study=study, is_selected=True
        )
        ops = self._scoped(ctx, "ebios_rm.OperationalScenario").filter(
            ebios_rm_study=study
        )
        done = {
            "framing": bool((study.objectives or "").strip()),
            "assets": self._study_assets(ctx, study).filter(type="PR").exists(),
            "feared_events": fe.exists(),
            "gravity": fe.exists() and not fe.filter(gravity__lt=0).exists(),
            "baseline": bool((study.observation or "").strip())
            or study.compliance_assessments.exists(),
            "rotos": self._scoped(ctx, "ebios_rm.RoTo")
            .filter(ebios_rm_study=study)
            .exists(),
            "stakeholders": self._scoped(ctx, "ebios_rm.Stakeholder")
            .filter(ebios_rm_study=study)
            .exists(),
            # every strategic scenario needs an attack path, or it never reaches workshop 4
            "strategic_scenarios": self._scoped(ctx, "ebios_rm.StrategicScenario")
            .filter(ebios_rm_study=study)
            .exists()
            and not self._pathless(ctx, study),
            "operational_scenarios": aps.exists()
            and not aps.exclude(operational_scenario__likelihood__gte=0).exists()
            and ops.exists(),
        }
        assessments = self._scoped(ctx, "core.RiskAssessment").filter(
            ebios_rm_study=study
        )
        scenarios = self._scoped(ctx, "core.RiskScenario").filter(
            risk_assessment__in=assessments
        )
        done["risk_assessment"] = assessments.exists()
        done["treatment"] = (
            scenarios.exists() and not scenarios.filter(treatment="open").exists()
        )
        for step, _, _ in STEPS:
            if step not in skipped and not done[step]:
                return step
        return None

    def _study_assets(self, ctx, study):
        return self._scoped(ctx, "core.Asset").filter(id__in=study.assets.values("id"))

    def _drop_unstated_ratings(
        self, ctx, study, step: str, items: list[dict]
    ) -> list[dict]:
        """A rating the user never gave is dropped, not recorded: kept only when the user's recent
        messages name its criterion or one of its levels (code, name or translation, from the
        study's matrix and the tool's default scales). The same for any model."""
        fields = RATINGS.get(step)
        if not fields:
            return items
        said = " ".join(
            [m.get("content", "") for m in ctx.history if m.get("role") == "user"][-3:]
            + [ctx.user_message]
        )
        said = f" {_norm(said)} "
        kept = []
        for item in items:
            item = dict(item)
            for field, words in fields.items():
                if item.get(field) in (None, "", []):
                    continue
                tokens = set(words) | self._level_words(study, field)
                if not any(_mentions(said, t) for t in tokens):
                    item.pop(field)
            kept.append(item)
        return kept

    def _level_words(self, study, field: str) -> set[str]:
        """Codes, names and translated names of a rating's levels in the study's matrix."""
        axis = {
            "gravity": "impact",
            "likelihood": "probability",
            "residual_likelihood": "probability",
        }
        try:
            matrix = study.risk_matrix.parse_json_translated()
        except Exception:
            return set()
        if field in axis:
            levels = matrix.get(axis[field], [])
        else:
            levels = ((matrix.get("ebios_rm") or {}).get("ro_to") or {}).get(field, [])
        words = set()
        for level in levels:
            words |= {_norm(level.get("abbreviation")), _norm(level.get("name"))}
            words |= {
                _norm(t.get("name")) for t in (level.get("translations") or {}).values()
            }
        return {w for w in words if w}

    def _pathless(self, ctx, study) -> list[str]:
        """Strategic scenarios with no attack path yet."""
        return list(
            self._scoped(ctx, "ebios_rm.StrategicScenario")
            .filter(ebios_rm_study=study, attack_paths__isnull=True)
            .values_list("name", flat=True)
        )

    def _levels(self, study, axis: str) -> list[dict]:
        try:
            return study.risk_matrix.parse_json_translated()[axis]
        except Exception as e:
            logger.warning("ebios_scale_unavailable", error=e)
            return []

    def _scale(self, study, axis: str) -> list[str]:
        return [_label(level) for level in self._levels(study, axis)]

    def _level_index(self, study, axis: str, value) -> int | None:
        """Index of the level the model named: "G4", "Critical", "G4 Critical", or 4 for "G4"."""
        levels = self._levels(study, axis)
        wanted = _norm(value)
        for i, level in enumerate(levels):
            names = (level.get("abbreviation"), level.get("name"), _label(level))
            if wanted in {_norm(n) for n in names}:
                return i
        digits = re.findall(r"\d+", wanted)[:1]
        for i, level in enumerate(levels):
            if (
                digits
                and re.findall(r"\d+", _norm(level.get("abbreviation")))[:1] == digits
            ):
                return i
        return None

    def _study_snapshot(self, ctx, study, step) -> tuple[str, str]:
        assets = list(self._study_assets(ctx, study).values_list("name", "type"))
        fes = list(
            self._scoped(ctx, "ebios_rm.FearedEvent")
            .filter(ebios_rm_study=study)
            .values_list("name", "gravity")
        )
        rotos = list(self._scoped(ctx, "ebios_rm.RoTo").filter(ebios_rm_study=study))
        stakeholders = list(
            self._scoped(ctx, "ebios_rm.Stakeholder")
            .filter(ebios_rm_study=study)
            .select_related("entity")
        )
        aps = list(
            self._scoped(ctx, "ebios_rm.AttackPath").filter(
                ebios_rm_study=study, is_selected=True
            )
        )
        impact = self._scale(study, "impact")
        lines = [
            f"Study: {study.name}",
            f"Description: {(study.description or '')[:600]}",
            f"Objectives: {(study.objectives or '(none)')[:600]}",
            "Assets: " + (", ".join(f"{n} ({t})" for n, t in assets) or "(none)"),
            "Feared events: "
            + (
                ", ".join(
                    f"{n} (gravity {impact[g] if 0 <= g < len(impact) else 'not rated'})"
                    for n, g in fes
                )
                or "(none)"
            ),
            "Risk origin / target objective couples: "
            + (
                "; ".join(
                    f"[{i + 1}] {_roto_label(r, ctx.user_lang[:2])}"
                    for i, r in enumerate(rotos)
                )
                or "(none)"
            ),
            "Stakeholders: "
            + (", ".join(s.entity.name for s in stakeholders) or "(none)"),
            "Attack paths: " + (", ".join(a.name for a in aps) or "(none)"),
        ]
        extra = ""
        if step == "assets":
            domain_assets = (
                self._scoped(ctx, "core.Asset")
                .filter(folder=study.folder)
                .exclude(id__in=study.assets.values("id"))
                .values_list("name", "type")[:40]
            )
            extra = "Assets of the domain not yet in the study: " + (
                ", ".join(f"{n} ({t})" for n, t in domain_assets) or "(none)"
            )
        elif step in ("gravity", "feared_events"):
            extra = "Gravity scale of the study: " + "; ".join(
                self._scale(study, "impact")
            )
        elif step == "treatment":
            risks = self._scoped(ctx, "core.RiskScenario").filter(
                risk_assessment__ebios_rm_study=study
            )
            extra = (
                "Risks to treat: "
                + (
                    "; ".join(r.name for r in risks.filter(treatment="open"))
                    or "(none)"
                )
                + "\nLikelihood scale of the study: "
                + "; ".join(self._scale(study, "probability"))
            )
        elif step == "operational_scenarios":
            extra = "Likelihood scale of the study: " + "; ".join(
                self._scale(study, "probability")
            )
        elif step == "rotos":
            extra = "Risk origins available: " + ", ".join(
                self._terms("ROTO_RISK_ORIGIN")
            )
        elif step == "stakeholders":
            from .ebios_rm_assist import _can_write

            existing = [
                e.name
                for e in self._scoped(ctx, "tprm.Entity").exclude(builtin=True)[:40]
            ]
            can_add = _can_write(ctx.scope.user, study.folder, ("add_entity",))
            extra = (
                "Stakeholder categories available (use the code): "
                + ", ".join(
                    f"{code} ({label})" if label else code
                    for code, label in self._category_labels(ctx.user_lang[:2])
                )
                + "\nThird parties already in the tool: "
                + (", ".join(existing) or "(none)")
                + (
                    ""
                    if can_add
                    else "\nThis user may not create third parties: only those above can become "
                    "stakeholders; tell the user so, and that an administrator can add the others."
                )
            )
        return "\n".join(lines), extra + ("\n" if extra else "")

    def _terms(self, field_path: str) -> list[str]:
        Terminology = apps.get_model("core", "Terminology")
        return list(
            Terminology.objects.filter(
                field_path=getattr(Terminology.FieldPath, field_path), is_visible=True
            ).values_list("name", flat=True)
        )

    def _stakeholders_possible(self, ctx, study) -> bool:
        from .ebios_rm_assist import _can_write

        return self._scoped(ctx, "tprm.Entity").exclude(
            builtin=True
        ).exists() or _can_write(ctx.scope.user, study.folder, ("add_entity",))

    def _existing_names(self, ctx, step: str) -> set:
        """Names already in the study for this step's objects (to mark new vs updated)."""
        state = self._load_state(ctx) or {}
        study_id = (state.get("data") or {}).get("study_id")
        model = EXISTING.get(step)
        if not model or not study_id:
            return set()
        rows = self._scoped(ctx, model)
        if model == "core.Asset":
            Study = apps.get_model("ebios_rm", "EbiosRMStudy")
            study = Study.objects.filter(id=study_id).first()
            # the domain's assets are reused, not created again
            rows = rows.filter(folder=study.folder) if study else rows.none()
        else:
            rows = rows.filter(ebios_rm_study_id=study_id)
        return {_norm(o.name) for o in rows}

    def _category_labels(self, lang: str) -> list[tuple[str, str]]:
        Terminology = apps.get_model("core", "Terminology")
        return [
            (t.name, (t.translations or {}).get(lang, ""))
            for t in Terminology.objects.filter(
                field_path=Terminology.FieldPath.ENTITY_RELATIONSHIP, is_visible=True
            )
        ]

    def _term_translations(self, lang: str) -> dict:
        Terminology = apps.get_model("core", "Terminology")
        return {
            t.name: (t.translations or {}).get(lang)
            for t in Terminology.objects.filter(
                field_path=Terminology.FieldPath.ENTITY_RELATIONSHIP
            )
            if (t.translations or {}).get(lang)
        }

    def _term(self, field_path: str, name: str):
        Terminology = apps.get_model("core", "Terminology")
        terms = Terminology.objects.filter(
            field_path=getattr(Terminology.FieldPath, field_path), is_visible=True
        )
        wanted = _norm(name)

        def names(t):  # the code, as read ("organized crime"), and its translations
            known = {_norm(t.name), _norm(t.name.replace("_", " "))}
            known |= {_norm(v) for v in (t.translations or {}).values()}
            known |= {
                _norm(lang.get(t.name))
                for lang in RISK_ORIGINS.values()
                if lang.get(t.name)
            }
            return known

        exact = next((t for t in terms if wanted in names(t)), None)
        if exact:
            return exact
        # a near spelling ("contracteur" for "contractor"): the closest known name, if close
        import difflib

        candidates = {n: t for t in terms for n in names(t) if n}
        close = difflib.get_close_matches(wanted, list(candidates), n=1, cutoff=0.75)
        if close:
            return candidates[close[0]]
        return next(
            (t for t in terms if _norm(t.name) == wanted),
            next(
                (
                    t
                    for t in terms
                    if wanted and (wanted in _norm(t.name) or _norm(t.name) in wanted)
                ),
                None,
            ),
        )

    # ── Proposal display and recording ───────────────────────────────

    def _render_proposal(
        self, ctx, step: str, items: list[dict], study
    ) -> Iterator[SSEEvent]:
        """Field names from a fixed table, the user's data as written: no model translation here."""
        lang = ctx.user_lang[:2]
        labels = LABELS.get(lang, LABELS["en"])
        terms = {**RISK_ORIGINS.get(lang, {}), **self._term_translations(lang)}
        existing = self._existing_names(ctx, step)
        rotos = list(self._scoped(ctx, "ebios_rm.RoTo").filter(ebios_rm_study=study))
        terms["roto"] = {i + 1: _roto_label(r, lang) for i, r in enumerate(rotos)}
        yield self._token("Here is what I propose to record:")
        lines = ["\n"]
        for item in items:
            shown = [
                f"{labels.get(k, k.replace('_', ' '))}: {_shown(_readable(k, v, labels, terms), labels)}"
                for k, v in item.items()
                if k
                not in (
                    "name",
                    "entity",
                    "feared_event",
                    "attack_path",
                    "risk_scenario",
                    "new",
                )
                and v not in (None, "", [])
            ]
            title = _item_title(
                {
                    **item,
                    "risk_origin": _readable(
                        "risk_origin", item.get("risk_origin"), labels, terms
                    ),
                }
            )
            mark = ""
            if title and step in EXISTING:
                known = _norm(title) in existing
                mark = f" _({labels['existing' if known else 'new']})_"
            if title:
                lines.append(
                    f"- **{title}**{mark}" + (" — " + ", ".join(shown) if shown else "")
                )
            else:
                lines += [f"- {part}" for part in shown]
        yield SSEEvent(type="token", content="\n".join(lines) + "\n\n")
        buttons = BUTTONS.get(ctx.user_lang[:2], BUTTONS["en"])
        yield self._pending_choice(
            field="ebios_proposal",
            label="Record it, or tell me what to change.",
            items=[{"id": key, "name": name} for key, name in buttons.items()],
        )

    def _apply(self, ctx, study, step: str, items: list[dict]) -> str:
        """Record item by item: an item updates the study's object of the same name, or creates it;
        one bad item never loses the others, and the summary says exactly what was recorded."""
        from django.db import transaction

        from .ebios_rm_assist import _can_write

        self._missing_entities = []
        self._expected_names = set()  # filled by a recorder that could not match a name
        self._can_add_entity = _can_write(ctx.scope.user, study.folder, ("add_entity",))
        self._can_add_fe = _can_write(
            ctx.scope.user, study.folder, ("add_fearedevent",)
        )
        lang = ctx.user_lang[:2] if ctx.user_lang[:2] in NOUNS else "en"
        words = NOUNS[lang]
        recorded, failed = [], []
        from django.utils import timezone

        batch = _BATCH_START.set(timezone.now())
        try:
            for item in items[:1] if step in ("framing", "baseline") else items:
                _refresh_scope(
                    ctx
                )  # objects created by earlier items must be visible to this one
                try:
                    with transaction.atomic():
                        if getattr(self, f"_record_{step}")(ctx, study, item):
                            title = _item_title(self._titled(item, lang))
                            level = self._level_index(
                                study, "impact", item.get("gravity")
                            )
                            if title and level is not None:
                                title += f" ({self._scale(study, 'impact')[level]})"
                            recorded.append(title)
                        else:
                            failed.append(_item_title(self._titled(item, lang)) or step)
                except Exception as e:
                    logger.warning(
                        "ebios_facilitation_record_failed", step=step, error=e
                    )
                    failed.append(_item_title(self._titled(item, lang)) or step)
        finally:
            _BATCH_START.reset(batch)
        names = ", ".join(f"**{r}**" for r in recorded if r)
        noun = words[step]
        parts = [
            f"{words['recorded']} {noun} — {names}"
            if names
            else (
                f"{words['recorded']} {noun}"
                if recorded
                else f"{words['nothing']} ({noun})"
            )
        ]
        if failed:
            parts.append(f"{words['failed']} {', '.join(failed)}")
        if failed and self._expected_names:
            parts.append(
                f"{words['expected']} {', '.join(sorted(self._expected_names))}"
            )
        if self._missing_entities:
            parts.append(
                f"{', '.join(self._missing_entities)} : {words['missing_entities']}"
            )
        return "; ".join(parts)

    def _titled(self, item: dict, lang: str) -> dict:
        if not item.get("risk_origin"):
            return item
        terms = {**RISK_ORIGINS.get(lang, {}), **self._term_translations(lang)}
        labels = LABELS.get(lang, LABELS["en"])
        return {
            **item,
            "risk_origin": _readable("risk_origin", item["risk_origin"], labels, terms),
        }

    def _by_name(self, ctx, model_label, study):
        return {
            _norm(o.name): o
            for o in self._scoped(ctx, model_label).filter(ebios_rm_study=study)
        }

    def _record_framing(self, ctx, study, item):
        # the model may nest values (exclusions, deadline...): store them as text people read
        if item.get("objectives"):
            study.objectives = _as_text(item["objectives"])
        # scope, deadline, budget...: whatever else the model returned belongs with the constraints
        rest = {k: v for k, v in item.items() if k != "objectives" and v}
        if rest:
            study.constraints_hypotheses = _as_text(
                rest.get("constraints") if list(rest) == ["constraints"] else rest
            )
        study.save(update_fields=["objectives", "constraints_hypotheses", "updated_at"])
        return True

    def _record_assets(self, ctx, study, item):
        from .ebios_rm_assist import _can_write

        Asset = apps.get_model("core", "Asset")
        name = str(item.get("name") or "").strip()
        asset = next(
            (
                a
                for a in self._scoped(ctx, "core.Asset").filter(folder=study.folder)
                if _norm(a.name) == _norm(name)
            ),
            None,
        )
        if (
            not asset
            and name
            and _can_write(ctx.scope.user, study.folder, ("add_asset",))
        ):
            asset = Asset.objects.create(
                name=name[:200],
                type="PR" if item.get("type") == "PR" else "SP",
                folder=study.folder,
            )
        if asset:
            study.assets.add(asset)
            supported = [_norm(n) for n in item.get("supports") or []]
            if supported and _can_write(
                ctx.scope.user, study.folder, ("change_asset",)
            ):
                asset.parent_assets.add(
                    *[
                        a
                        for a in self._study_assets(ctx, study).filter(type="PR")
                        if _norm(a.name) in supported
                    ]
                )
        return bool(asset)

    def _record_feared_events(self, ctx, study, item):
        FearedEvent = apps.get_model("ebios_rm", "FearedEvent")
        name = str(item.get("name") or "").strip()
        if not name:
            return False
        fe = _find(self._by_name(ctx, "ebios_rm.FearedEvent", study), name)
        if fe is None:
            fe = FearedEvent.objects.create(
                ebios_rm_study=study, name=name[:200], is_selected=True
            )
        if item.get("description"):
            fe.description = str(item["description"])
            fe.save(update_fields=["description", "updated_at"])
        assets = {_norm(a.name): a for a in self._study_assets(ctx, study)}
        fe.assets.add(
            *[a for a in (_find(assets, n) for n in item.get("assets") or []) if a]
        )
        fe.is_selected = True  # an event the user keeps is retained, as a new one is
        gravity = self._level_index(study, "impact", item.get("gravity"))
        if gravity is not None:  # users often rate while naming the event
            fe.gravity = gravity
        fe.save(update_fields=["gravity", "is_selected", "updated_at"])
        return True

    def _record_gravity(self, ctx, study, item):
        FearedEvent = apps.get_model("ebios_rm", "FearedEvent")
        name = str(item.get("feared_event") or "").strip()
        fe = _find(self._by_name(ctx, "ebios_rm.FearedEvent", study), name)
        if (
            fe is None and name and self._can_add_fe
        ):  # a feared event named while rating
            fe = FearedEvent.objects.create(
                ebios_rm_study=study, name=name[:200], is_selected=True
            )
        gravity = self._level_index(study, "impact", item.get("gravity"))
        if fe is None or gravity is None:
            return False
        fe.gravity = gravity
        fe.is_selected = True  # a rated event is retained
        fe.save(update_fields=["gravity", "is_selected", "updated_at"])
        return True

    def _record_baseline(self, ctx, study, item):
        frameworks = [str(f) for f in item.get("frameworks") or []]
        gaps = [str(g) for g in item.get("gaps") or []]
        audits = [
            a
            for a in self._scoped(ctx, "core.ComplianceAssessment")
            .filter(folder=study.folder)
            .select_related("framework")
            if any(_norm(f) in _norm(a.framework.name) for f in frameworks if f)
        ]
        study.compliance_assessments.add(*audits)
        fr = ctx.user_lang[:2] == "fr"
        base, gap = (
            ("Socle de sécurité", "Écarts connus")
            if fr
            else ("Security baseline", "Known gaps")
        )
        lines = [f"{base} : {', '.join(frameworks)}"] if frameworks else []
        lines += [f"{gap} : {'; '.join(gaps)}"] if gaps else []
        if lines:
            study.observation = "\n".join(lines)
            study.save(update_fields=["observation", "updated_at"])
        return bool(lines or audits)

    def _record_rotos(self, ctx, study, item):
        RoTo = apps.get_model("ebios_rm", "RoTo")
        origin = self._term("ROTO_RISK_ORIGIN", item.get("risk_origin"))
        objective = str(item.get("target_objective") or "").strip()
        if not origin or not objective:
            return False
        roto = (
            self._scoped(ctx, "ebios_rm.RoTo")
            .filter(
                ebios_rm_study=study, risk_origin=origin, target_objective=objective
            )
            .first()
        ) or RoTo(ebios_rm_study=study, risk_origin=origin, target_objective=objective)
        for field in ("motivation", "resources", "activity"):
            if roto._state.adding or field in item:
                setattr(roto, field, _level(item.get(field), 1, 4))
        roto.is_selected = True
        roto.save()
        fes = self._by_name(ctx, "ebios_rm.FearedEvent", study)
        roto.feared_events.add(
            *[f for f in (_find(fes, n) for n in item.get("feared_events") or []) if f]
        )
        return True

    def _record_stakeholders(self, ctx, study, item):
        Entity = apps.get_model("tprm", "Entity")
        Stakeholder = apps.get_model("ebios_rm", "Stakeholder")
        category = self._term("ENTITY_RELATIONSHIP", item.get("category"))
        name = str(item.get("entity") or "").strip()
        if not category or not name:
            return False
        entity = next(
            (
                e
                for e in self._scoped(ctx, "tprm.Entity").exclude(builtin=True)
                if _norm(e.name) == _norm(name)
            ),
            None,
        )
        if entity is None:
            if not self._can_add_entity:
                self._missing_entities.append(name)
                return False
            entity = Entity.objects.create(name=name[:200], folder=study.folder)
        stakeholder = (
            self._scoped(ctx, "ebios_rm.Stakeholder")
            .filter(ebios_rm_study=study, entity=entity, category=category)
            .first()
        ) or Stakeholder(ebios_rm_study=study, entity=entity, category=category)
        for key, low, default in (
            ("dependency", 0, 0),
            ("penetration", 0, 0),
            ("maturity", 1, 1),
            ("trust", 1, 1),
        ):
            if stakeholder._state.adding or key in item:
                setattr(
                    stakeholder,
                    f"current_{key}",
                    _level(item.get(key), low, 4, default=default),
                )
        stakeholder.is_selected = True  # the user just retained it
        stakeholder.save()
        return True

    def _record_strategic_scenarios(self, ctx, study, item):
        StrategicScenario = apps.get_model("ebios_rm", "StrategicScenario")
        AttackPath = apps.get_model("ebios_rm", "AttackPath")
        rotos = list(self._scoped(ctx, "ebios_rm.RoTo").filter(ebios_rm_study=study))
        index, name = item.get("roto"), str(item.get("name") or "").strip()
        valid_couple = isinstance(index, int) and 1 <= index <= len(rotos)
        fes = self._by_name(ctx, "ebios_rm.FearedEvent", study)
        scenario = _find(self._by_name(ctx, "ebios_rm.StrategicScenario", study), name)
        if scenario is None:
            if not name or not valid_couple:  # a new scenario needs its couple
                return False
            scenario = StrategicScenario(ebios_rm_study=study, name=name[:200])
        scenario.description = str(
            item.get("description") or scenario.description or ""
        )
        if valid_couple:
            scenario.ro_to_couple = rotos[index - 1]
        couple_events = scenario.ro_to_couple.feared_events
        scenario.focused_feared_event = next(
            (
                fe
                for fe in (
                    _find(fes, item.get("feared_event")),
                    scenario.focused_feared_event,
                )
                if fe and couple_events.filter(id=fe.id).exists()
            ),
            None,
        )
        scenario.save()
        stakeholders = {
            _norm(s.entity.name): s
            for s in self._scoped(ctx, "ebios_rm.Stakeholder")
            .filter(ebios_rm_study=study)
            .select_related("entity")
        }
        paths = self._by_name(ctx, "ebios_rm.AttackPath", study)
        for path in item.get("attack_paths") or []:
            if not isinstance(path, dict) or not path.get("name"):
                continue
            attack_path = _find(paths, path["name"])
            if attack_path and attack_path.strategic_scenario_id != scenario.id:
                continue  # names are unique in the study: this one is another scenario's
            attack_path = attack_path or AttackPath.objects.create(
                ebios_rm_study=study,
                strategic_scenario=scenario,
                name=str(path["name"])[:200],
                is_selected=True,
            )
            attack_path.stakeholders.add(
                *[
                    x
                    for x in (
                        _find(stakeholders, n) for n in path.get("stakeholders") or []
                    )
                    if x
                ]
            )
        return True

    def _record_operational_scenarios(self, ctx, study, item):
        OperationalScenario = apps.get_model("ebios_rm", "OperationalScenario")
        path = _find(
            self._by_name(ctx, "ebios_rm.AttackPath", study), item.get("attack_path")
        )
        if path is None:
            return False
        scenario, _ = OperationalScenario.objects.get_or_create(
            attack_path=path, defaults={"ebios_rm_study": study, "is_selected": True}
        )
        scenario.operating_modes_description = str(item.get("description") or "")
        level = self._level_index(study, "probability", item.get("likelihood"))
        if level is not None:
            # A direct rating: without it, save() recomputes likelihood from operating modes
            scenario.likelihood_forced = level
        scenario.save()
        return True

    def _record_risk_assessment(self, ctx, study, item):
        """Through the risk assessment API view, as the user: the same validation, permissions and
        generation from the operational scenarios as the study page's button."""
        from core.views import RiskAssessmentViewSet

        view = RiskAssessmentViewSet()
        view.request, view.format_kwarg, view.action, view.kwargs = (
            ctx.request,
            None,
            "create",
            {},
        )
        serializer = view.get_serializer(
            data={
                "name": str(item.get("name") or study.name)[:200],
                "folder": str(study.folder_id),
                "risk_matrix": str(study.risk_matrix_id),
                "ebios_rm_study": str(study.id),
            }
        )
        serializer.is_valid(raise_exception=True)
        view.perform_create(serializer)
        return True

    def _record_treatment(self, ctx, study, item):
        from .ebios_rm_assist import _can_write

        AppliedControl = apps.get_model("core", "AppliedControl")
        treatment = str(item.get("treatment") or "").lower()
        if treatment not in ("mitigate", "accept", "avoid", "transfer"):
            return False
        scenarios = {
            _norm(r.name): r
            for r in self._scoped(ctx, "core.RiskScenario").filter(
                risk_assessment__ebios_rm_study=study
            )
        }
        scenario = _find(scenarios, item.get("risk_scenario"))
        if scenario is None:
            self._expected_names |= {r.name for r in scenarios.values()}
            return False
        folder = scenario.risk_assessment.folder
        if not _can_write(ctx.scope.user, folder, ("change_riskscenario",)):
            return False
        scenario.treatment = treatment
        level = self._level_index(study, "probability", item.get("residual_likelihood"))
        if level is not None:
            scenario.residual_proba = level
            if scenario.residual_impact < 0:
                scenario.residual_impact = scenario.current_impact
        scenario.save()
        controls = {
            _norm(c.name): c
            for c in self._scoped(ctx, "core.AppliedControl").filter(folder=folder)
        }
        can_add = _can_write(ctx.scope.user, folder, ("add_appliedcontrol",))
        for name in item.get("measures") or []:
            name = str(name).strip()
            control = _find(controls, name)
            if control is None and name and can_add:
                control = AppliedControl.objects.create(
                    name=name[:200], folder=folder, status="to_do"
                )
                controls[_norm(name)] = control
            if control is not None:
                scenario.applied_controls.add(control)
        return True

    def _draft_remaining(self, ctx, study_obj) -> Iterator[SSEEvent]:
        """The user asked for a full draft: the one-shot generator fills the empty workshops."""
        study = {
            "id": str(study_obj.id),
            "name": study_obj.name,
            "description": study_obj.description or "",
            "folder_id": str(study_obj.folder_id),
            "risk_matrix_id": str(study_obj.risk_matrix_id),
            "obj": study_obj,
        }
        created = {
            k: []
            for k in (
                "assets",
                "feared_events",
                "rotos",
                "strategic_scenarios",
                "attack_paths",
                "operational_scenarios",
            )
        }
        yield from self._run_workshops(ctx, study, created, start_from="feared_events")


NOUNS = {
    "en": {
        "recorded": "Recorded in the study:",
        "nothing": "Nothing recorded",
        "failed": "not recorded:",
        "missing_entities": "not in the third parties yet, and you may not create them",
        "expected": "names in the study:",
        "framing": "objectives",
        "assets": "assets",
        "feared_events": "feared events",
        "gravity": "gravity",
        "baseline": "security baseline",
        "rotos": "risk origin / target objective couples",
        "stakeholders": "stakeholders",
        "strategic_scenarios": "strategic scenarios",
        "operational_scenarios": "operational scenarios",
        "risk_assessment": "risk assessment",
        "treatment": "risk treatment",
    },
    "fr": {
        "recorded": "Enregistré dans l'étude :",
        "nothing": "Rien n'a été enregistré",
        "failed": "non enregistré :",
        "missing_entities": "pas encore dans les tiers, et vous ne pouvez pas les créer",
        "expected": "noms dans l'étude :",
        "framing": "objectifs",
        "assets": "biens",
        "feared_events": "événements redoutés",
        "gravity": "gravité",
        "baseline": "socle de sécurité",
        "rotos": "couples source de risque / objectif visé",
        "stakeholders": "parties prenantes",
        "strategic_scenarios": "scénarios stratégiques",
        "operational_scenarios": "scénarios opérationnels",
        "risk_assessment": "analyse de risques",
        "treatment": "traitement du risque",
    },
}


def _readable(key, value, labels, terms=None):
    """Codes as a reader says them: PR/SP, risk origins and categories in the user's language."""
    if key == "type" and value in ("PR", "SP"):
        return labels[value]
    if key == "treatment" and isinstance(value, str):
        return labels.get(value.lower(), value)
    if key in ("risk_origin", "category") and isinstance(value, str):
        terms = terms or {}
        return (
            terms.get(value)
            or terms.get(value.lower().replace(" ", "_"))
            or value.replace("_", " ")
        )
    if key == "roto" and isinstance(value, int):
        return (terms or {}).get("roto", {}).get(value, value)
    return value


def _roto_label(roto, lang: str) -> str:
    """A couple as the user reads it: "crime organisé - extorquer une rançon", not the stored code."""
    code = roto.risk_origin.name
    origin = (
        RISK_ORIGINS.get(lang, {}).get(code.lower())
        or (roto.risk_origin.translations or {}).get(lang)
        or code.replace("_", " ")
    )
    return f"{origin} - {roto.target_objective}"


def _item_title(item: dict) -> str:
    return str(
        item.get("name")
        or item.get("risk_scenario")
        or item.get("entity")
        or item.get("feared_event")
        or item.get("attack_path")
        or " → ".join(
            str(item[k]).replace("_", " ")
            for k in ("risk_origin", "target_objective")
            if item.get(k)
        )
        or ""
    )


def _as_text(value) -> str:
    if isinstance(value, dict):
        return "\n".join(
            f"{k.replace('_', ' ')}: {_as_text(v)}" for k, v in value.items() if v
        )
    if isinstance(value, list):
        return "; ".join(_as_text(v) for v in value)
    return str(value)


def _shown(value, labels=None) -> str:
    """A proposal value as a reader wants it, not as JSON."""
    labels = labels or {}
    if isinstance(value, list):
        return "; ".join(_shown(v, labels) for v in value)
    if isinstance(value, dict):
        name = value.get("name", "")
        rest = ", ".join(
            f"{labels.get(k, k.replace('_', ' '))}: {_shown(v, labels)}"
            for k, v in value.items()
            if k != "name" and v
        )
        return f"{name} ({rest})" if rest else str(name)
    return str(value)


def _label(level: dict) -> str:
    """A scale level as users read it: "G4 Critical", or "4 - critical" when the name holds the code."""
    code, name = level.get("abbreviation") or "", level.get("name") or ""
    return name if code and code in name else f"{code} {name}".strip()


def _level(value, low: int, high: int, default: int = 0) -> int:
    return value if isinstance(value, int) and low <= value <= high else default
