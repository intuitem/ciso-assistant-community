"""Audit starter.pbit before committing a fresh Power BI Desktop export.

A .pbit is a zip whose DataModelSchema is UTF-16LE JSON. Desktop bakes the
authoring session into it, so an export can silently ship the maintainer's own
instance URL or relationships invented by autodetect.

Usage: python automation/powerbi/samples/audit_pbit.py [path/to/starter.pbit]
"""

import json
import pathlib
import re
import sys
import zipfile

EXPECTED_RELATIONSHIPS = {
    ("Applied Controls", "folder_id", "Folders", "id"),
    ("Compliance Assessments", "folder_id", "Folders", "id"),
    ("Compliance Assessments", "framework_id", "Frameworks", "id"),
    (
        "Requirement Assessments",
        "compliance_assessment_id",
        "Compliance Assessments",
        "id",
    ),
    ("Risk Scenario - Threat", "risk_scenario_id", "Risk Scenarios", "id"),
    ("Risk Scenario - Threat", "threat_id", "Threats", "id"),
}

URL_LITERAL = re.compile(r"CisoAssistant\.Contents\s*\(\s*\"")
POSITIONAL_NAV = re.compile(r"\{\d+\}\[Data\]")
PARAMETER_DEFAULT = re.compile(r'^\s*"([^"]*)"')

ALLOWED_DEFAULTS = {"https://localhost:8443", "https://ciso-assistant.example.com"}


def partition_expressions(model):
    for table in model["tables"]:
        for partition in table.get("partitions", []):
            expression = partition.get("source", {}).get("expression")
            if expression is None:
                continue
            if isinstance(expression, list):
                expression = "\n".join(expression)
            yield table["name"], expression


def main():
    path = pathlib.Path(
        sys.argv[1]
        if len(sys.argv) > 1
        else pathlib.Path(__file__).with_name("starter.pbit")
    )
    with zipfile.ZipFile(path) as archive:
        model = json.loads(archive.read("DataModelSchema").decode("utf-16-le"))["model"]

    errors = []

    parameters = {
        e["name"]: e for e in model.get("expressions", []) if e.get("kind") == "m"
    }
    if "BaseUrl" not in parameters:
        errors.append(
            "no BaseUrl parameter: the template will not prompt for an instance URL on open"
        )
    else:
        expression = parameters["BaseUrl"]["expression"]
        if isinstance(expression, list):
            expression = "\n".join(expression)
        default = PARAMETER_DEFAULT.match(expression)
        if not default:
            errors.append(f"BaseUrl has no literal default value: {expression!r}")
        elif default.group(1) not in ALLOWED_DEFAULTS:
            errors.append(
                f"BaseUrl defaults to {default.group(1)!r} — the export kept the authoring instance; "
                f"reset it to one of {sorted(ALLOWED_DEFAULTS)} before File → Export"
            )
        if "IsParameterQuery=true" not in expression:
            errors.append(
                "BaseUrl is a plain query, not a parameter: no prompt on template open"
            )

    for table, expression in partition_expressions(model):
        if URL_LITERAL.search(expression):
            errors.append(
                f"{table}: hardcoded URL in CisoAssistant.Contents — must be CisoAssistant.Contents(BaseUrl)"
            )
        positional = POSITIONAL_NAV.search(expression)
        if positional:
            errors.append(
                f"{table}: positional navigation ({positional.group()}) — "
                'must select by key ({[Name = "..."]}[Data]), or reordering the connector navigator '
                "silently repoints this query at another table"
            )

    found = {
        (r["fromTable"], r["fromColumn"], r["toTable"], r["toColumn"])
        for r in model.get("relationships", [])
        if "LocalDateTable" not in r["toTable"]
    }
    for relationship in sorted(found - EXPECTED_RELATIONSHIPS):
        errors.append(
            f"unexpected relationship (autodetect phantom?): {' '.join(relationship)}"
        )
    for relationship in sorted(EXPECTED_RELATIONSHIPS - found):
        errors.append(f"missing relationship: {' '.join(relationship)}")

    if errors:
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        return 1

    print(
        f"{path.name}: {len(found)} relationships, BaseUrl parameter present, no hardcoded URLs"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
