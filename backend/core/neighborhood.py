"""Relation neighbourhood for the graph drawer: one pass, minimal columns."""

from django.core.exceptions import ObjectDoesNotExist
from django.db import models

from iam.models import RoleAssignment

# Beyond this the graph shows a "+N" drawn from the count.
PER_RELATION = 25


class Relation:
    __slots__ = ("accessor", "url_model", "verb", "inbound")

    def __init__(self, accessor: str, url_model: str, verb: str, inbound: bool = False):
        self.accessor = accessor
        self.url_model = url_model
        self.verb = verb
        self.inbound = inbound


# Opt-in per model; anything else falls back to its own forward relations.
NEIGHBOURHOOD: dict[str, list[Relation]] = {
    "core.AppliedControl": [
        Relation("reference_control", "reference-controls", "templates", inbound=True),
        Relation("assets", "assets", "protects"),
        Relation("evidences", "evidences", "evidenced by"),
        Relation("owner", "actors", "owned by"),
        Relation("security_exceptions", "security-exceptions", "excepted by"),
        Relation("objectives", "organisation-objectives", "serves"),
        Relation("incidents", "incidents", "responds to"),
        Relation("folder", "folders", "scopes", inbound=True),
        Relation(
            "requirement_assessments",
            "requirement-assessments",
            "satisfied by",
            inbound=True,
        ),
        Relation("risk_scenarios", "risk-scenarios", "mitigated by", inbound=True),
        Relation("findings", "findings", "remediated by", inbound=True),
        Relation("task_templates", "task-templates", "maintains", inbound=True),
        # DocumentContainer.applied_controls; `documents` belongs to the Policy proxy.
        Relation(
            "control_documents", "document-containers", "documented by", inbound=True
        ),
    ],
    "core.RiskScenario": [
        Relation("risk_assessment", "risk-assessments", "comprises", inbound=True),
        Relation("assets", "assets", "targets"),
        Relation("threats", "threats", "driven by"),
        Relation("applied_controls", "applied-controls", "mitigated by"),
        Relation(
            "existing_applied_controls", "applied-controls", "already mitigated by"
        ),
        Relation("incidents", "incidents", "realised by"),
        Relation("owner", "actors", "owned by"),
        Relation("security_exceptions", "security-exceptions", "excepted by"),
        Relation(
            "operational_scenario",
            "operational-scenarios",
            "derived from",
            inbound=True,
        ),
        Relation("folder", "folders", "scopes", inbound=True),
        Relation("vulnerabilities", "vulnerabilities", "exploits"),
    ],
    "core.Asset": [
        Relation("parent_assets", "assets", "supports", inbound=True),
        Relation("child_assets", "assets", "supported by"),
        Relation("applied_controls", "applied-controls", "protected by"),
        Relation("solutions", "solutions", "delivered by"),
        Relation("personal_data", "personal-data", "holds"),
        Relation("owner", "actors", "owned by"),
        Relation("asset_class", "asset-classes", "classifies", inbound=True),
        Relation("security_exceptions", "security-exceptions", "excepted by"),
        Relation("folder", "folders", "scopes", inbound=True),
        Relation("risk_scenarios", "risk-scenarios", "targets", inbound=True),
        Relation("findings", "findings", "affects", inbound=True),
        Relation("vulnerabilities", "vulnerabilities", "exposes", inbound=True),
        Relation(
            "compliance_assessments", "compliance-assessments", "audits", inbound=True
        ),
        Relation("incidents", "incidents", "hit by", inbound=True),
        Relation("documents", "document-containers", "documented by", inbound=True),
    ],
    "doc_management.DocumentContainer": [
        Relation("assets", "assets", "documents"),
        Relation("applied_controls", "applied-controls", "documents"),
        Relation("task_templates", "task-templates", "documents"),
        Relation("processings", "processings", "documents"),
        Relation("policies", "policies", "documents"),
        Relation("classification", "classification-levels", "classifies", inbound=True),
        Relation("folder", "folders", "scopes", inbound=True),
    ],
}

GENERIC_SKIP = {
    "filtering_labels",
    "custom_field_values",
    "commitments",
    "comments",
    "logentry",
}

_URL_MODEL_CACHE: dict[str, str] = {}
_EXPANDABLE_CACHE: dict[str, bool] = {}


def _url_model_for(model: type[models.Model]) -> str:
    """Hint only; the frontend re-resolves from the model name."""
    label = model._meta.label
    if label not in _URL_MODEL_CACHE:
        _URL_MODEL_CACHE[label] = model._meta.verbose_name_plural.lower().replace(
            " ", "-"
        )
    return _URL_MODEL_CACHE[label]


def _generic_relations(model: type[models.Model]) -> list[Relation]:
    """Forward only: the reverse side of an arbitrary model is unvetted."""
    out = []
    for field in model._meta.get_fields():
        if not field.is_relation or field.auto_created or field.related_model is None:
            continue
        if field.name in GENERIC_SKIP:
            continue
        out.append(
            Relation(
                field.name,
                _url_model_for(field.related_model),
                field.name.replace("_", " "),
            )
        )
    return out


def _expandable(model: type[models.Model]) -> bool:
    """Whether expanding a node of this model could show anything."""
    label = model._meta.label
    if label not in _EXPANDABLE_CACHE:
        _EXPANDABLE_CACHE[label] = bool(
            NEIGHBOURHOOD.get(label) or _generic_relations(model)
        )
    return _EXPANDABLE_CACHE[label]


def _rows(queryset: models.QuerySet, limit: int) -> tuple[list[dict], int]:
    model = queryset.model
    names = {f.name for f in model._meta.get_fields()}
    total = queryset.count()
    if "name" in names:
        columns = ["id", "name"] + (["ref_id"] if "ref_id" in names else [])
        rows = list(queryset.values(*columns)[:limit])
        out = [
            {
                "id": str(r["id"]),
                "name": r.get("name") or "",
                "ref": r.get("ref_id") or None,
            }
            for r in rows
        ]
        # Some models leave name empty and let __str__ derive the label.
        blank = [r["id"] for r in out if not r["name"]]
        if blank:
            for obj in queryset.model.objects.filter(pk__in=blank):
                for r in out:
                    if r["id"] == str(obj.pk):
                        r["name"] = str(obj)
        return out, total
    # __str__ usually walks a FK: join them in rather than one query per row.
    related = [f.name for f in model._meta.fields if f.is_relation]
    rows = queryset.select_related(*related)[:limit] if related else queryset[:limit]
    return (
        [
            {"id": str(o.pk), "name": str(o), "ref": getattr(o, "ref_id", None)}
            for o in rows
        ],
        total,
    )


def build(obj, user) -> dict:
    model = type(obj)
    relations = NEIGHBOURHOOD.get(model._meta.label) or _generic_relations(model)

    root = {
        "id": str(obj.pk),
        "urlModel": _url_model_for(model),
        "model": model._meta.model_name,
        "name": getattr(obj, "name", None) or str(obj),
        "ref": getattr(obj, "ref_id", None),
    }

    nodes: dict[str, dict] = {}
    links: list[dict] = []
    totals: dict[str, int] = {}
    # One scoping query per target model, not per relation.
    viewable: dict[str, models.QuerySet] = {}

    for rel in relations:
        try:
            attr = getattr(obj, rel.accessor)
        except AttributeError, ObjectDoesNotExist:
            continue
        if attr is None:
            continue

        if isinstance(attr, models.Manager):
            queryset = attr.all()
        elif isinstance(attr, models.Model):
            queryset = type(attr).objects.filter(pk=attr.pk)
        else:
            continue

        # Scoping costs three queries; skip it for a relation that holds nothing.
        if not queryset.exists():
            continue

        target = queryset.model
        label = target._meta.label
        if label not in viewable:
            try:
                viewable[label] = RoleAssignment.get_viewable_object_ids(user, target)
            except NotImplementedError:
                # Outside IAM (reference data): nothing to scope against.
                viewable[label] = None
            except Exception:
                continue  # never fall back to unscoped
        if viewable[label] is not None:
            queryset = queryset.filter(id__in=viewable[label])

        group = f"{rel.verb}|{rel.url_model}"
        rows, total = _rows(queryset, PER_RELATION)
        if not total:
            continue
        totals[group] = totals.get(group, 0) + total
        for row in rows:
            if row["id"] == root["id"]:
                continue
            nodes.setdefault(
                row["id"],
                {
                    "id": row["id"],
                    "urlModel": rel.url_model,
                    "name": row["name"],
                    "ref": row["ref"],
                    "group": group,
                    "model": target._meta.model_name,
                    "expandable": _expandable(target),
                },
            )
            links.append(
                {"source": row["id"], "target": root["id"], "verb": rel.verb}
                if rel.inbound
                else {"source": root["id"], "target": row["id"], "verb": rel.verb}
            )

    return {
        "root": root,
        "nodes": list(nodes.values()),
        "links": links,
        "totals": totals,
    }
