"""Import an export of the CNIL PIA software (github.com/LINCnil/pia) as a draft
DPIA response on a processing.

The export is `{pia, answers[], measures[], evaluations[], comments[]}`, joined by
`reference_to`. Answers point at the numbered questions of the CNIL default
questionnaire (111…346), which our DPIA form follows page for page. Questions are
bound by URN leaves (`<page>:<question>`), so a cloned form imports the same way.
Nothing lands on the processing itself: the draft is reviewed, submitted and
accepted like any other, and its targets then apply.
"""

import re
from html.parser import HTMLParser

from django.utils.dateparse import parse_date

from core.models import AppliedControl, Question
from core.utils import apply_answers_dict


class PiaImportError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


# CNIL question id -> our "<page>:<question>" leaf. Several ids on one leaf are
# joined, the ones the question does not ask for under a label.
TEXT_QUESTIONS = {
    111: "overview:benefits",
    112: "overview:benefits",
    113: "overview:standards",
    122: "data:lifecycle",  # before 121: the question itself comes first, unlabelled
    121: "data:lifecycle",
    123: "data:supports",
    211: "proportionality:purposes",
    212: "proportionality:purposes",
    213: "proportionality:minimisation",
    214: "proportionality:accuracy",
    215: "proportionality:retention",
    221: "rights:information",
    222: "rights:consent",
    223: "rights:access_portability",
    224: "rights:rectification_erasure",
    225: "rights:restriction_objection",
    226: "rights:processors",
    227: "rights:transfers",
}

# CNIL items 3.2 / 3.3 / 3.4: questions 3n1…3n6.
RISKS = {2: "illegitimate_access", 3: "unwanted_modification", 4: "disappearance"}

# CNIL item -> our page, to say what an action plan line is about.
ITEM_PAGES = {
    "1.1": "overview",
    "1.2": "data",
    "2.1": "proportionality",
    "2.2": "rights",
    **{f"3.{n}": page for n, page in RISKS.items()},
}

# The words the import writes into the answers, punctuation included: saved there,
# so in the importer's language, which only the caller knows. English by default.
DEFAULT_LABELS = {
    "responsibilities": "Responsibilities:",
    "dataProcessed": "Data processed:",
    "legalBasis": "Legal basis:",
    "favourable": "favourable",
    "unfavourable": "unfavourable",
}
# The CNIL answers our form folds into a neighbouring question.
QUESTION_LABELS = {112: "responsibilities", 121: "dataProcessed", 212: "legalBasis"}


def parse_labels(value) -> dict:
    """The caller's `labels`, each a short string; English for those left out."""
    if value is None:
        value = {}
    if not isinstance(value, dict) or not all(
        isinstance(value.get(key, ""), str) and len(value.get(key, "")) <= 100
        for key in DEFAULT_LABELS
    ):
        raise PiaImportError("invalidRequest")
    return {
        key: value.get(key, "").strip() or default
        for key, default in DEFAULT_LABELS.items()
    }


class _TextExtractor(HTMLParser):
    BLOCKS = {"p", "div", "br", "li", "ul", "ol", "tr", "h1", "h2", "h3", "h4"}

    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in self.BLOCKS:
            self.parts.append("\n")
        if tag == "li":
            self.parts.append("- ")

    def handle_endtag(self, tag):
        if tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)


def html_to_text(value) -> str:
    """CNIL answers are HTML from a rich-text editor; ours are plain text."""
    if not value or not isinstance(value, str):
        return ""
    parser = _TextExtractor()
    parser.feed(value)
    parser.close()
    lines = [
        re.sub(r"[ \t\r\f\v]+", " ", line).strip()
        for line in "".join(parser.parts).split("\n")
    ]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _plain(value) -> str:
    """The validation page's fields are plain textareas: a `<` there is text."""
    return value.strip() if isinstance(value, str) else ""


def _join(*parts) -> str:
    return "\n\n".join(p for p in parts if p)


def parse_export(data) -> dict:
    """Checks the shape of a CNIL export; raises PiaImportError with a fixed code."""
    if not isinstance(data, dict) or not isinstance(data.get("pia"), dict):
        raise PiaImportError("piaInvalidFile")
    for key in ("answers", "measures", "evaluations", "comments"):
        if data.get(key) is None:
            data[key] = []
        if not isinstance(data[key], list) or not all(
            isinstance(row, dict) for row in data[key]
        ):
            raise PiaImportError("piaInvalidFile")

    def check(value, kind):
        if value is not None and not isinstance(value, kind):
            raise PiaImportError("piaInvalidFile")

    for row in data["answers"]:
        check(row.get("data"), dict)
        check((row.get("data") or {}).get("list"), list)
    for row in data["evaluations"]:
        check(row.get("gauges"), dict)
    # shortcut: only the CNIL default questionnaire is mapped; a custom structure
    # numbers its own questions. Upgrade if customers bring custom structures.
    if data["pia"].get("structure_id"):
        raise PiaImportError("piaCustomStructure")
    return data


def import_pia(response, processing, data, user, *, labels) -> dict:
    """Fill the draft `response` from the parsed export `data`, in the words of
    `labels` (see parse_labels). Creates the CNIL measures as applied controls in
    the processing's domain (reusing a control of the same name there). Returns
    counts and the kinds of content left out."""
    folder = processing.folder
    questions = {}
    pages = {}
    for question in Question.objects.filter(
        page__quick_form_id=response.quick_form_id
    ).select_related("page"):
        if not question.page.urn or not question.urn:
            continue
        page_leaf = question.page.urn.rsplit(":", 1)[-1]
        questions[f"{page_leaf}:{question.urn.rsplit(':', 1)[-1]}"] = question
        pages[page_leaf] = question.page
    if "measures:measures" not in questions:
        raise PiaImportError("piaFormMismatch")

    pia = data["pia"]
    answers = {}
    for row in data["answers"]:
        try:
            answers[int(row.get("reference_to"))] = row.get("data") or {}
        except TypeError, ValueError:
            continue
    evaluations = {str(e.get("reference_to")): e for e in data["evaluations"]}
    skipped = set()
    values = {}

    def put(leaf, value):
        if value in (None, "", []):
            return
        if leaf in questions:
            values[questions[leaf].urn] = value
        else:
            skipped.add("unmappedAnswers")

    def text_of(qid):
        return html_to_text(answers.get(qid, {}).get("text"))

    def list_of(qid):
        items = answers.get(qid, {}).get("list") or []
        return [str(i).strip() for i in items if str(i).strip()]

    merged = {}
    for qid, leaf in TEXT_QUESTIONS.items():
        text = text_of(qid)
        if text:
            key = QUESTION_LABELS.get(qid)
            merged.setdefault(leaf, []).append(f"{labels[key]} {text}" if key else text)
    for leaf, parts in merged.items():
        put(leaf, _join(*parts))

    # Measures (CNIL 3.1) -> applied controls, also matched by title from risks.
    controls_by_title = {}
    created = reused = 0
    for measure in data["measures"]:
        title = str(measure.get("title") or "").strip()[:200]
        if not title or title.lower() in controls_by_title:
            continue
        evaluation = evaluations.get(f"3.1.{measure.get('id')}", {})
        description = html_to_text(measure.get("content"))
        observation = _join(
            html_to_text(evaluation.get("evaluation_comment")),
            html_to_text(evaluation.get("action_plan_comment")),
        )
        eta = _date(evaluation.get("estimated_implementation_date"))
        # Names are unique per domain regardless of case (AbstractBaseModel.clean),
        # visible or not: matched the same way, or creating it fails.
        control = AppliedControl.objects.filter(
            folder=folder, name__iexact=title
        ).first()
        if control is None:
            control = AppliedControl.objects.create(
                folder=folder,
                name=title,
                description=description,
                observation=observation or None,
                eta=eta,
            )
            created += 1
        else:
            # Linked as it stands: what the file says of it is left out.
            if (
                description not in ("", control.description or "")
                or observation not in ("", control.observation or "")
                or eta not in (None, control.eta)
            ):
                skipped.add("reusedMeasureDetails")
            reused += 1
        controls_by_title[title.lower()] = control
    put("measures:measures", [str(c.pk) for c in controls_by_title.values()])

    action_plan = []
    for n, page in RISKS.items():
        base = 300 + n * 10
        for offset, field in ((1, "impacts"), (2, "threats"), (3, "sources")):
            put(f"{page}:{field}", ", ".join(list_of(base + offset)))
        # Keyed like the measures: cut to a control's name length.
        titles = [t[:200].lower() for t in list_of(base + 4)]
        picked = [controls_by_title[t] for t in titles if t in controls_by_title]
        if len(picked) < len(titles):
            skipped.add("unmatchedMeasures")
        put(f"{page}:measures", [str(c.pk) for c in picked])
        for offset, field in ((5, "severity"), (6, "likelihood")):
            put(f"{page}:{field}_justification", text_of(base + offset))
            put(
                f"{page}:{field}",
                _level(
                    questions.get(f"{page}:{field}"),
                    answers.get(base + offset, {}).get("gauge"),
                ),
            )
        evaluation = evaluations.get(f"3.{n}", {})
        gauges = evaluation.get("gauges") or {}
        # The evaluator's gauges place the risk once the measures are in place.
        put(
            f"{page}:residual_severity",
            _level(questions.get(f"{page}:residual_severity"), gauges.get("x")),
        )
        put(
            f"{page}:residual_likelihood",
            _level(questions.get(f"{page}:residual_likelihood"), gauges.get("y")),
        )

    for ref, evaluation in sorted(evaluations.items()):
        if ref.startswith("3.1."):
            continue
        if comment := html_to_text(evaluation.get("action_plan_comment")):
            # "3.2" is an item, "2.1.211" one of its questions: both under its page.
            page = pages.get(ITEM_PAGES.get(".".join(ref.split(".")[:2])))
            action_plan.append(
                f"{page.get_name_translated if page else ref} — {comment}"
            )
        if html_to_text(evaluation.get("evaluation_comment")):
            skipped.add("evaluationComments")

    status = {0: labels["unfavourable"], 1: labels["favourable"]}
    dpo_header = ", ".join(
        p
        for p in (
            str(pia.get("dpos_names") or "").strip(),
            status.get(_int(pia.get("dpo_status")), ""),
        )
        if p
    )
    put(
        "validation:dpo_opinion",
        _join(dpo_header, _plain(pia.get("dpo_opinion"))),
    )
    if pia.get("concerned_people_searched_opinion") in (False, 0, "0", "false"):
        put(
            "validation:views_not_sought_reason",
            _plain(pia.get("concerned_people_searched_content")),
        )
    else:
        people_header = ", ".join(
            p
            for p in (
                str(pia.get("people_names") or "").strip(),
                status.get(_int(pia.get("concerned_people_status")), ""),
            )
            if p
        )
        put(
            "validation:data_subject_views",
            _join(people_header, _plain(pia.get("concerned_people_opinion"))),
        )
    put(
        "validation:conditions",
        _join(
            _plain(pia.get("applied_adjustments")),
            _plain(pia.get("rejection_reason")),
            "\n".join(action_plan),
        ),
    )
    # The decision is the reviewer's judgement, never taken from the file.
    if data["comments"]:
        skipped.add("piaComments")

    apply_answers_dict(
        "response", response, {q.urn: q for q in questions.values()}, values, user=user
    )
    response.refresh_title_from_answers()
    response.recompute()
    return {
        "answers": len(values),
        "controls_created": created,
        "controls_reused": reused,
        "skipped": sorted(skipped),
    }


def _date(value):
    try:
        return parse_date(str(value or "")[:10])
    except ValueError:
        return None


def _int(value):
    try:
        return int(value)
    except TypeError, ValueError:
        return None


def _level(question, gauge):
    """CNIL gauge 1–4 (0 = not set) -> the choice URN at that rank of the scale."""
    gauge = _int(gauge)
    if question is None or not gauge:
        return None
    choices = list(question.choices.order_by("order").values_list("urn", flat=True))
    return choices[gauge - 1] if 0 < gauge <= len(choices) else None
