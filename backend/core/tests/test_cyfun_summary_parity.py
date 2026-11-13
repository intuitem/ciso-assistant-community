"""Our CyFun 2025 scores equal the CCB self-assessment tool's summary sheet
when both hold the same answers: the tool's own formulas are recomputed."""

import random
import re
from pathlib import Path
from unittest.mock import patch

import pytest
from django.urls import reverse
from knox.models import AuthToken
from openpyxl import load_workbook
from rest_framework.test import APIClient

from core import cyfun
from core.apps import startup
from iam.models import User, UserGroup
from core.models import (
    ComplianceAssessment,
    Folder,
    Framework,
    RequirementAssessment,
    StoredLibrary,
)

BACKEND = Path(__file__).resolve().parents[2]
CYFUN = BACKEND / "library/libraries/cyfun2025.yaml"
FUNCTION_SHEETS = ("GOVERN", "IDENTIFY", "PROTECT", "DETECT", "RESPOND", "RECOVER")

_REF = re.compile(r"(?:([A-Za-z]+)!)?\$?([A-Z]+)\$?(\d+)(?::\$?([A-Z]+)\$?(\d+))?")


class Workbook:
    """Evaluates the few Excel functions the CCB summary uses."""

    def __init__(self, workbook):
        self.wb = workbook
        self.cache = {}

    def value(self, sheet, cell):
        key = (sheet, cell)
        if key not in self.cache:
            raw = self.wb[sheet][cell].value
            self.cache[key] = (
                self._eval(sheet, raw[1:])
                if isinstance(raw, str) and raw.startswith("=")
                else raw
            )
        return self.cache[key]

    def _range(self, sheet, c1, r1, c2, r2):
        cells = self.wb[sheet][f"{c1}{r1}:{c2}{r2}"]
        return [self.value(sheet, c.coordinate) for row in cells for c in row]

    def _eval(self, sheet, formula):
        def ref(m):
            s = m.group(1) or sheet
            if m.group(4):
                return f"_rg({s!r},{m.group(2)!r},{m.group(3)},{m.group(4)!r},{m.group(5)})"
            return f"_v({s!r},'{m.group(2)}{m.group(3)}')"

        expr = _REF.sub(ref, re.sub(r"(?<![<>!=])=(?!=)", "==", formula))

        def nums(args):
            flat = []
            for a in args:
                flat.extend(a if isinstance(a, list) else [a])
            return [x for x in flat if isinstance(x, (int, float))]

        env = {
            "_v": self.value,
            "_rg": self._range,
            "IF": lambda c, a, b: a if c else b,
            "OR": lambda *a: any(a),
            "AVERAGE": lambda *a: sum(nums(a)) / len(nums(a)),
            "SUM": lambda *a: sum(nums(a)),
            "COUNT": lambda *a: len(nums(a)),
        }
        return eval(expr, env)  # noqa: S307 - formulas of a bundled, trusted template


@pytest.fixture
def basic_audit(db):
    stored = StoredLibrary.objects.filter(
        urn="urn:intuitem:risk:library:ccb-cyfun2025"
    ).first()
    if stored is None:
        stored, error = StoredLibrary.store_library_content(CYFUN.read_bytes())
        assert error is None
    assert stored.load() is None
    framework = Framework.objects.get(urn="urn:intuitem:risk:framework:ccb-cyfun2025")
    groups = ["B", "BK", "BG"]
    ca = ComplianceAssessment.objects.create(
        name="CyFun BASIC",
        framework=framework,
        folder=Folder.get_root_folder(),
        min_score=1,
        max_score=5,
        selected_implementation_groups=groups,
        **framework.default_scoring_for(groups),
    )
    ca.show_documentation_score = True
    ca.save()
    ca.create_requirement_assessments()
    return ca


@pytest.mark.django_db
def test_category_total_and_key_measure_scores_match_the_ccb_tool(basic_audit):
    ca = basic_audit
    template, requirement_column = cyfun.TEMPLATES["basic"]
    workbook = load_workbook(BACKEND / "core/templates/core" / template)

    ras = {
        ra.requirement.ref_id: ra
        for ra in RequirementAssessment.objects.filter(
            compliance_assessment=ca, requirement__assessable=True
        ).select_related("requirement")
        if "B" in (ra.requirement.implementation_groups or [])
    }
    key_measures = {
        ref for ref, ra in ras.items() if "BK" in ra.requirement.implementation_groups
    }
    rng = random.Random(7)
    not_applicable = set(rng.sample(sorted(set(ras) - key_measures), 3))
    for ref_id, ra in ras.items():
        if ref_id in not_applicable:
            ra.result, ra.score, ra.documentation_score = "not_applicable", None, None
        else:
            ra.result = "compliant"
            ra.score, ra.documentation_score = rng.randint(1, 5), rng.randint(1, 5)
        ra.is_scored = True
    RequirementAssessment.objects.bulk_update(
        ras.values(), ["result", "score", "documentation_score", "is_scored"]
    )

    # Same answers in the tool: F = documentation, G = implementation
    for sheet in FUNCTION_SHEETS:
        ws = workbook[sheet]
        for row in range(3, ws.max_row + 1):
            ref_id = cyfun.normalize_ref_id(ws.cell(row, requirement_column).value)
            if ref_id:
                ra = ras[ref_id]
                na = ref_id in not_applicable
                ws.cell(row, 6).value = "N/A" if na else ra.documentation_score
                ws.cell(row, 7).value = "N/A" if na else ra.score
    tool = Workbook(workbook)
    summary = "BASIC Summary"

    ca.refresh_from_db()
    all_ras = list(
        RequirementAssessment.objects.filter(
            compliance_assessment=ca, requirement__assessable=True
        ).select_related("requirement")
    )

    def ours(prefix):
        subset = [
            ra
            for ra in all_ras
            if ra.requirement.ref_id.startswith(prefix)
            and "B" in (ra.requirement.implementation_groups or [])
        ]
        return ca.get_scores_for(subset)

    checked = 0
    for row in range(5, 22):
        label = workbook[summary].cell(row, 2).value
        code = re.search(r"\(([A-Z]{2}\.[A-Z]{2})\)", label).group(1)
        scores = ours(code + "-")
        assert scores["documentation_score"] == pytest.approx(
            tool.value(summary, f"E{row}"), abs=0.01
        ), code
        assert scores["implementation_score"] == pytest.approx(
            tool.value(summary, f"F{row}"), abs=0.01
        ), code
        assert scores["maturity_score"] == pytest.approx(
            tool.value(summary, f"D{row}"), abs=0.01
        ), code
        checked += 1
    assert checked == 17

    total = ca.get_scores_for(
        [ra for ra in all_ras if "B" in (ra.requirement.implementation_groups or [])]
    )
    assert total["maturity_score"] == pytest.approx(tool.value(summary, "M4"), abs=0.01)

    for row in range(25, 38):
        ref_id = cyfun.normalize_ref_id(workbook[summary].cell(row, 12).value)
        scores = ca.get_scores_for([ras[ref_id]])
        assert scores["maturity_score"] == pytest.approx(
            tool.value(summary, f"O{row}"), abs=0.01
        ), ref_id


@pytest.fixture
def admin_client(basic_audit):
    startup(sender=None, **{})
    admin = User.objects.create_superuser("admin@cyfun-summary-tests.com")
    group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = group.folder
    admin.save()
    group.user_set.add(admin)
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=admin)[1]}"
    )
    return client


@pytest.mark.django_db
def test_group_breakdown_lists_key_measures_against_their_target(
    basic_audit, admin_client
):
    url = reverse(
        "compliance-assessments-implementation-groups-breakdown",
        kwargs={"pk": str(basic_audit.pk)},
    )
    groups = {g["ref_id"]: g for g in admin_client.get(url).json()["groups"]}
    key_measures = groups["BK"]
    assert key_measures["selected"] is True
    assert key_measures["target_score"] == 2.5
    assert {r["id"] for r in key_measures["requirements"]} == {
        str(ra.id)
        for ra in basic_audit.requirement_assessments.filter(
            requirement__assessable=True
        )
        if "BK" in (ra.requirement.implementation_groups or [])
    }
    assert len(key_measures["requirements"]) == 13
    assert groups["I"]["selected"] is False
    assert groups["I"]["requirements"] == []  # outside the audit: not listed


@pytest.mark.django_db
def test_group_breakdown_hides_fields_the_viewer_cannot_see(basic_audit, admin_client):
    url = reverse(
        "compliance-assessments-implementation-groups-breakdown",
        kwargs={"pk": str(basic_audit.pk)},
    )
    with patch(
        "core.views.is_field_visible_to", side_effect=lambda ca, f, role: f != "score"
    ):
        groups = admin_client.get(url).json()["groups"]
    rows = next(g for g in groups if g["ref_id"] == "BK")["requirements"]
    assert all(r["maturity_score"] is None for r in rows)
    assert all(r["implementation_score"] is None for r in rows)
    assert any(r["result"] for r in rows)
