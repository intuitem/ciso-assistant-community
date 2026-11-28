from chat.views import _match_workflow
from chat.workflows.base import SSEEvent, Workflow, discussion_language, localize_event


def test_ebios_method_question_is_not_pre_routed():
    # Questions that merely mention EBIOS RM go to the model, not the study-creation workflow.
    for question in (
        "Dans EBIOS RM, à quel atelier évalue-t-on la vraisemblance des scénarios opérationnels ?",
        "What are the five EBIOS RM workshops?",
        "Help me run an EBIOS RM study",
    ):
        assert _match_workflow(question, None) is None


class FakeLLM:
    def __init__(self, reply):
        self.reply, self.prompts = reply, []

    def generate(self, prompt, context, **kwargs):
        self.prompts.append(prompt)
        return self.reply(prompt) if callable(self.reply) else self.reply


def test_discussion_language_reads_recent_user_messages():
    llm = FakeLLM("fr")
    history = [{"role": "user", "content": "Lance une étude EBIOS RM"}]
    assert discussion_language(llm, "Halvard Devices", history, fallback="en") == "fr"
    assert "Lance une étude EBIOS RM" in llm.prompts[0]


def test_discussion_language_falls_back_on_unknown_reply():
    assert discussion_language(FakeLLM("klingon"), "Qapla'", [], fallback="de") == "de"


def test_fixed_workflow_text_is_translated_generated_text_is_not():
    llm = FakeLLM(lambda p: '{"text": "Quelle matrice de risque ?"}')
    wf = Workflow()
    cache = {}
    fixed = localize_event(wf._token("Which risk matrix? "), llm, "fr", cache)
    assert fixed.content == "Quelle matrice de risque ? "  # trailing space kept
    generated = SSEEvent(type="token", content="Bonjour")
    assert localize_event(generated, llm, "fr", cache) is generated
    choice = wf._pending_choice(
        "matrix", "Select a risk matrix", [{"id": 1, "name": "5x5"}]
    )
    out = localize_event(choice, llm, "fr", cache)
    assert out.content["label"] == "Quelle matrice de risque ?"
    assert out.content["items"] == [{"id": 1, "name": "5x5"}]
    english = wf._token("Which risk matrix?")
    assert localize_event(english, llm, "en", cache) is english


def test_record_button_needs_no_model(monkeypatch):
    from types import SimpleNamespace

    import chat.workflows.ebios_rm_assist as assist

    applied = []
    workflow = assist.EbiosRMAssistWorkflow()
    state = {
        "step": "facilitate",
        "data": {
            "study_id": "s1",
            "phase": "proposed",
            "proposal": [{}],
            "proposal_step": "gravity",
        },
    }
    monkeypatch.setattr(workflow, "_load_state", lambda ctx: state)
    monkeypatch.setattr(workflow, "_save_state", lambda *a: None)
    monkeypatch.setattr(workflow, "_clear_state", lambda *a: None)
    monkeypatch.setattr(workflow, "_next_step", lambda ctx, s, skipped: None)
    monkeypatch.setattr(
        workflow,
        "_call_llm",
        lambda *a: (_ for _ in ()).throw(AssertionError("model called")),
    )
    monkeypatch.setattr(workflow, "_apply", lambda *a: applied.append(a[2]) or "ok")
    monkeypatch.setattr(assist, "_can_write", lambda *a: True)
    ctx = SimpleNamespace(
        scope=SimpleNamespace(user=None),
        history=[],
        user_message="Enregistrer",
        user_lang="fr",
    )
    list(workflow._facilitate(ctx, SimpleNamespace(id="s1", folder=None)))
    assert applied == ["gravity"]


def test_scale_levels_are_read_by_code_name_or_number():
    from types import SimpleNamespace

    from chat.workflows.ebios_rm_assist import EbiosRMAssistWorkflow

    levels = [
        {"abbreviation": f"G{i}", "name": n}
        for i, n in enumerate(["Minor", "Significant", "Important", "Critical"], 1)
    ]
    study = SimpleNamespace(
        risk_matrix=SimpleNamespace(parse_json_translated=lambda: {"impact": levels})
    )
    workflow = EbiosRMAssistWorkflow()
    assert [
        workflow._level_index(study, "impact", v)
        for v in ("G4", "critical", 4, "G4 Critical", "G9")
    ] == [3, 3, 3, 3, None]


def test_every_step_has_a_question_in_each_language():
    import string

    from chat.workflows.ebios_facilitation import QUESTIONS, STEPS

    filled = {
        "study",
        "domain_assets",
        "business_values",
        "unrated",
        "gravity_scale",
        "likelihood_scale",
        "origins",
        "entities",
        "rotos",
        "paths",
        "operational_count",
        "open_risks",
    }
    for lang, questions in QUESTIONS.items():
        assert set(questions) == {step for step, _, _ in STEPS}, lang
        for text in questions.values():
            assert {f for _, f, _, _ in string.Formatter().parse(text) if f} <= filled


def test_names_match_despite_small_paraphrases():
    from chat.workflows.ebios_facilitation import _find

    paths = {
        "compromission de la télémaintenance d'hôpisoft": "p1",
        "accès internes": "p2",
    }
    assert _find(paths, "Compromission de la télémaintenance Hôpisoft") == "p1"
    assert _find(paths, "Attaque du portail patient") is None
    assert _find(paths, "") is None


def test_ratings_the_user_never_gave_are_dropped():
    from types import SimpleNamespace

    from chat.workflows.ebios_rm_assist import EbiosRMAssistWorkflow

    matrix = {
        "impact": [{"abbreviation": f"G{i}", "name": f"g{i}"} for i in range(1, 5)],
        "ebios_rm": {
            "ro_to": {
                "motivation": [
                    {"name": "Strong", "translations": {"fr": {"name": "Fort"}}}
                ],
                "resources": [
                    {"name": "Unlimited", "translations": {"fr": {"name": "Illimité"}}}
                ],
            }
        },
    }
    study = SimpleNamespace(
        risk_matrix=SimpleNamespace(parse_json_translated=lambda: matrix)
    )
    workflow = EbiosRMAssistWorkflow()
    ctx = SimpleNamespace(
        history=[], user_message="Crime organisé, motivation forte. Rien d'autre."
    )
    couple = {
        "risk_origin": "organized_crime",
        "target_objective": "rançon",
        "motivation": 4,
        "resources": 4,
    }
    kept = workflow._drop_unstated_ratings(ctx, study, "rotos", [couple])[0]
    assert kept["motivation"] == 4 and "resources" not in kept
    ctx.user_message = "Fuite de données : G4"
    fe = {"name": "Fuite", "gravity": "G4"}
    assert (
        workflow._drop_unstated_ratings(ctx, study, "feared_events", [fe])[0]["gravity"]
        == "G4"
    )
    ctx.user_message = "Fuite de données de santé"
    assert (
        "gravity"
        not in workflow._drop_unstated_ratings(ctx, study, "feared_events", [fe])[0]
    )


def test_unsupported_language_leaves_fixed_text_untouched():
    event = Workflow()._token("Which risk matrix?")
    llm = FakeLLM(lambda p: (_ for _ in ()).throw(AssertionError("model called")))
    assert localize_event(event, llm, "xx", {}) is event
