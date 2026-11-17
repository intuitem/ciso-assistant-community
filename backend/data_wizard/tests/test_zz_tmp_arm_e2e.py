import glob, unicodedata
import pytest
from openpyxl import load_workbook
from data_wizard.tests.test_load_file_view import _post
from data_wizard.tests.test_templates import ebios_4x4_matrix  # noqa
from ebios_rm.models import *  # noqa
from core.models import AppliedControl, Asset

ROOT = (
    "/Users/abder/mydev/intuitem/staging/ciso-assistant-community/examples_arm_exports"
)


def table(folder, pat):
    for f in glob.glob(f"{ROOT}/{folder}*/**/*.xlsx", recursive=True):
        n = "".join(
            c for c in unicodedata.normalize("NFKD", f) if not unicodedata.combining(c)
        )
        if pat in n:
            return load_workbook(f, data_only=True).active


def col(ws, name, row=1):
    hdr = [c.value for c in ws[row]]
    i = hdr.index(name)
    return [
        str(r[i]).strip()
        for r in ws.iter_rows(min_row=3, values_only=True)
        if r[i] not in (None, "")
    ]


@pytest.mark.django_db
@pytest.mark.parametrize("n", [1, 2, 3])
def test_e2e(api_client, domain_folder, all_accessible, ebios_4x4_matrix, n):
    data = open(
        f"/private/tmp/claude-501/-Users-abder-mydev-intuitem-staging-ciso-assistant-community/2dd7d06d-4872-4a35-82e6-fe822b5d3dfe/scratchpad/armzips/study{n}.zip",
        "rb",
    ).read()
    resp = _post(
        api_client,
        data,
        "etude.zip",
        "EbiosRMStudyARM",
        domain_folder.id,
        HTTP_X_MATRIX_ID=str(ebios_4x4_matrix.id),
    )
    r = resp.json()["results"]
    print(f"\n#### STUDY {n} status={resp.status_code} errors={r.get('errors')}")
    print("WARN", [w.get("sheet") or w.get("file") for w in r.get("warnings", [])])
    study = EbiosRMStudy.objects.get(id=r["details"]["study"])

    def cmp(label, source, imported):
        s, i = set(source), set(imported)
        print(
            f"CHECK {label}: source={len(s)} imported={len(i)} missing={sorted(s - i)[:4]} extra={sorted(i - s)[:4]}"
        )

    cmp(
        "primary assets",
        [x[:200] for x in col(table(str(n), "valeurs metier"), "Nom")],
        Asset.objects.filter(type="PR").values_list("name", flat=True),
    )
    fe = [x for x in col(table(str(n), "redoutes"), "Évènement redouté") if x != "NA"]
    cmp(
        "feared events (non-NA)", fe, study.feared_events.values_list("name", flat=True)
    )
    cmp(
        "controls",
        col(table(str(n), "Mesures"), "Nom"),
        AppliedControl.objects.values_list("name", flat=True),
    )
    cmp(
        "scenarios",
        col(table(str(n), "scenarios"), "Nom"),
        StrategicScenario.objects.values_list("name", flat=True),
    )
    cmp(
        "stakeholders",
        col(table(str(n), "Menace"), "Partie prenante"),
        Stakeholder.objects.values_list("entity__name", flat=True),
    )
    ws = table(str(n), "couples")
    pairs = {
        (str(a).strip(), str(b).strip())
        for _, a, b, *rest in ws.iter_rows(min_row=3, values_only=True)
        if a and b
    }
    print(
        "CHECK roto pairs",
        len(pairs),
        "imported",
        RoTo.objects.count(),
        "cotation/FE",
        [
            (x.motivation, x.resources, x.feared_events.count())
            for x in RoTo.objects.all()
        ],
    )
    print(
        "LINK FE gravity",
        sorted(study.feared_events.values_list("gravity", flat=True)),
        "FE w/o assets",
        study.feared_events.filter(assets=None).count(),
    )
    print(
        "LINK attack paths",
        AttackPath.objects.count(),
        "per scenario",
        [s.attack_paths.count() for s in StrategicScenario.objects.all()],
        "stakeholder scores",
        list(
            Stakeholder.objects.values_list("current_dependency", "current_penetration")
        ),
    )


@pytest.mark.django_db
def test_full_export(api_client, domain_folder, all_accessible, ebios_4x4_matrix):
    data = open(
        "/Users/abder/mydev/intuitem/staging/ciso-assistant-community/Export global BYOD - 2026-11-02 105742 - Confidentiel ORES.xlsx",
        "rb",
    ).read()
    r = _post(
        api_client,
        data,
        "x.xlsx",
        "EbiosRMStudyARM",
        domain_folder.id,
        HTTP_X_MATRIX_ID=str(ebios_4x4_matrix.id),
    ).json()["results"]
    d = r["details"]
    print("\n#### FULL errors", r["errors"], "warnings", r["warnings"])
    print(
        "FULL",
        {k: v for k, v in d.items() if k.endswith("created")},
        "roto FE links",
        sum(x.feared_events.count() for x in RoTo.objects.all()),
    )
