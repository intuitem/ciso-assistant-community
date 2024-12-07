import os
from icecream import ic
from .models import *
from math import ceil


def gen_audit_context(id):
    context = dict()
    audit = ComplianceAssessment.objects.get(id=id)

    authors = ", ".join([a.email for a in audit.authors.all()])
    reviewers = ", ".join([a.email for a in audit.reviewers.all()])

    cnt_per_result = audit.get_requirements_result_count()
    ic(cnt_per_result)
    total = sum([res[0] for res in cnt_per_result])
    perc_res = [
        ceil((res[0] / total) * 100) if total > 0 else 0 for res in cnt_per_result
    ]
    ic(perc_res)
    context = {
        "name": audit.name,
        "framework": audit.framework.name,
        "date": now().strftime("%Y-%m-%d %H:%M"),
        "contributors": f"{authors}\n{reviewers}",
        "description": audit.description,
        "domain": audit.project,
        "observation": audit.observation,
        "req": {
            "total": total,
            "compliant": cnt_per_result[3][0],
            "part_compliant": cnt_per_result[1][0],
            "non_compliant": cnt_per_result[2][0],
            "not_applicable": cnt_per_result[4][0],
            "not_assessed": cnt_per_result[0][0],
            "compliant_p": perc_res[3],
            "part_compliant_p": perc_res[1],
            "non_compliant_p": perc_res[2],
            "not_applicable_p": perc_res[4],
            "not_assessed_p": perc_res[0],
        },
    }

    return context
