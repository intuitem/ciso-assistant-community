"""Facts: the subject's own records a form page shows, read-only, next to its
questions, so a form assesses what the platform already holds instead of asking
for it again. Read live while the response is a draft, frozen on submit: the
submitted response keeps what was assessed even as the subject changes.

A page lists the facts it shows by key in `facts`. Apps register theirs.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Fact:
    key: str
    #: app_label.ModelName of the subject the fact reads.
    subject_model: str
    #: i18n key of the fact's title.
    label: str
    #: Related manager on the subject giving the rows.
    relation: str
    #: Attributes shown, in order; `name` reads str() on a model without one.
    columns: tuple[str, ...]


FACTS: dict[str, Fact] = {}


def register_fact(fact: Fact) -> Fact:
    FACTS[fact.key] = fact
    return fact


def _i18n_key(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(part.capitalize() for part in rest)


def _cell(row, column: str):
    if column == "name" and not hasattr(row, "name"):
        return str(row)
    value = getattr(row, column, None)
    if hasattr(value, "all"):
        return ", ".join(str(item) for item in value.all())
    if value is None or isinstance(value, bool):
        return value
    # Choice values are i18n keys: the client translates them.
    return str(value)


def read_fact(fact: Fact, subject) -> dict:
    return {
        "label": fact.label,
        "columns": [_i18n_key(c) for c in fact.columns],
        "rows": [
            [_cell(row, c) for c in fact.columns]
            for row in getattr(subject, fact.relation).all()
        ],
    }


def page_fact_keys(quick_form) -> list[str]:
    from core.models import QuickFormPage

    keys = []
    for facts in QuickFormPage.objects.filter(quick_form=quick_form).values_list(
        "facts", flat=True
    ):
        keys += [k for k in facts or [] if k not in keys]
    return keys


def live_facts(response) -> dict:
    """{key: fact data} for the facts the form's pages show, read from the
    subject. A fact for another model than the subject's is left out."""
    keys = page_fact_keys(response.quick_form)
    subject = response.subject if keys else None
    if subject is None:
        return {}
    label = subject._meta.label
    return {
        key: read_fact(FACTS[key], subject)
        for key in keys
        if key in FACTS and FACTS[key].subject_model == label
    }


def facts_for(response) -> dict:
    """What the pages show: frozen once submitted, live before."""
    if response.facts_snapshot is not None:
        return response.facts_snapshot
    return live_facts(response)


def freeze_facts(response) -> list[str]:
    """Snapshot the facts on submit. Returns the fields to save."""
    response.facts_snapshot = live_facts(response)
    return ["facts_snapshot"]


def facts_error(pages) -> str | None:
    """Why a page's `facts` cannot work, or None."""
    for page in pages or []:
        facts = page.get("facts")
        if facts is None:
            continue
        if not isinstance(facts, list) or not all(isinstance(k, str) for k in facts):
            return f"page {page.get('urn')}: facts must be a list of keys"
        unknown = [k for k in facts if k not in FACTS]
        if unknown:
            return f"page {page.get('urn')}: unknown facts {', '.join(unknown)}"
    return None
