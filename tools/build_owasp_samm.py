#!/usr/bin/env python3
"""Build the OWASP SAMM framework library from the official model repository.

Source: github.com/owaspsamm/core at a pinned tag, one YAML file per object
linked by GUIDs: business functions > security practices > streams (A/B) >
activities, each activity sitting at one maturity level (1-3) and measured by
one question whose answer set has four options valued 0 / 0.25 / 0.5 / 1.

Structure: function (depth 1, ref_id G/D/I/V/O) > practice (G-SM) > stream
(G-SM-A) > activity (G-SM-1-A, assessable). The question and its answer set
become a unique_choice question; the question's quality criteria become the
activity's typical evidence.

Scoring: requirement scores are integers, so SAMM values are scaled by 4
(add_score 0/1/2/4 on a 0-4 scale). Number outcome rules then give the SAMM
toolbox scorecard: overall, then each business function followed by its
practices. A practice scores the sum of its activities' SAMM values over its
streams (0-3), a function the mean of its practices, the overall score the mean
of the functions. Each rule reads its section's mean score times its scored
count, so unanswered activities count as 0, as in the toolbox.

Implementation groups are cumulative target levels: an activity at level n is
in groups n..3, so selecting "2" assesses levels 1 and 2 as SAMM intends.

Usage:
    python tools/build_owasp_samm.py [--source path/to/core] [--output-dir DIR]

Without --source, the pinned tag is downloaded from GitHub.
"""

import argparse
import io
import sys
import tarfile
import tempfile
import urllib.request
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LIBRARIES = ROOT / "backend/library/libraries"

SAMM_TAG = "v2.2.0"
SOURCE_URL = f"https://github.com/owaspsamm/core/archive/refs/tags/{SAMM_TAG}.tar.gz"

LIBRARY_ID = "owasp-samm-2.2"
URN_PREFIX = "urn:intuitem:risk"
URN_NODE = f"{URN_PREFIX}:req_node:{LIBRARY_ID}"
PUBLICATION_DATE = date(2026, 7, 6)
VERSION = 1

FUNCTION_CODES = {
    "Governance": "G",
    "Design": "D",
    "Implementation": "I",
    "Verification": "V",
    "Operations": "O",
}

# SAMM answer value -> (add_score, compute_result)
ANSWER_SCORING = {
    0: (0, "non_compliant"),
    0.25: (1, "partially_compliant"),
    0.5: (2, "partially_compliant"),
    1: (4, "compliant"),
}

# SAMM values per score point
SCALE = 4

# labelled with the SAMM value the score stands for
SCORES_DEFINITION = [
    {"score": 0, "name": "0", "description": "No"},
    {"score": 1, "name": "0.25", "description": "Some"},
    {"score": 2, "name": "0.5", "description": "At least half"},
    {"score": 4, "name": "1", "description": "Most or all"},
]

# Answers drive score and result, so the auditor sees both and nothing else;
# with status hidden, audit progress follows the computed result.
AUDITOR_ONLY = {"auditor": "edit", "respondent": "hidden"}
HIDDEN = {"auditor": "hidden", "respondent": "hidden"}
FIELD_VISIBILITY = {
    "score": AUDITOR_ONLY,
    "is_scored": AUDITOR_ONLY,
    "result": AUDITOR_ONLY,
    "status": HIDDEN,
    "extended_result": HIDDEN,
}

DESCRIPTION = (
    "OWASP Software Assurance Maturity Model (SAMM) v2.2. Measures and improves "
    "software security posture across 5 business functions, 15 security "
    "practices and 30 streams, with 90 activities at maturity levels 1 to 3. "
    "Each activity is answered on SAMM's four-option scale, scaled by 4 "
    "(0, 1, 2, 4). The overall, business function and practice scores (0-3) "
    "follow the SAMM toolbox scorecard and assume the audit's default average "
    "score calculation. Implementation groups are cumulative target maturity "
    "levels. "
    "https://owaspsamm.org"
)


def fetch(dest: Path) -> Path:
    with urllib.request.urlopen(SOURCE_URL, timeout=60) as response:
        payload = response.read()
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        archive.extractall(dest, filter="data")
    return next(dest.iterdir())


def load(source: Path) -> dict[str, list[dict]]:
    model = source / "model"
    if not model.is_dir():
        sys.exit(f"no model/ directory under {source}")
    kinds = (
        "business_functions",
        "security_practices",
        "streams",
        "maturity_levels",
        "practice_levels",
        "activities",
        "questions",
        "answer_sets",
    )
    return {
        kind: [
            yaml.safe_load(path.read_text(encoding="utf-8"))
            for path in sorted((model / kind).glob("*.yml"))
        ]
        for kind in kinds
    }


def text(value) -> str:
    # YAML 1.1 reads a bare "No" answer as False
    if value is False:
        return "No"
    return str(value).strip()


def by_id(items: list[dict]) -> dict[str, dict]:
    return {item["id"]: item for item in items}


def validate(data: dict[str, list[dict]]) -> None:
    expected = {
        "business_functions": 5,
        "security_practices": 15,
        "streams": 30,
        "maturity_levels": 3,
        "practice_levels": 45,
        "activities": 90,
        "questions": 90,
    }
    errors = [
        f"{kind}: expected {count}, found {len(data[kind])}"
        for kind, count in expected.items()
        if len(data[kind]) != count
    ]
    if names := {f["name"] for f in data["business_functions"]} ^ set(FUNCTION_CODES):
        errors.append(f"unexpected business functions: {sorted(names)}")
    per_activity = Counter(q["activity"] for q in data["questions"])
    activity_ids = {a["id"] for a in data["activities"]}
    if set(per_activity) != activity_ids or set(per_activity.values()) != {1}:
        errors.append("each activity must have exactly one question")
    answer_sets = by_id(data["answer_sets"])
    for question in data["questions"]:
        answer_set = answer_sets.get(question["answerSet"])
        if answer_set is None:
            errors.append(f"question {question['id']}: unknown answer set")
            continue
        values = sorted(v["value"] for v in answer_set["values"])
        if values != sorted(ANSWER_SCORING):
            errors.append(f"answer set {answer_set['id']}: unexpected values {values}")
    per_stream = Counter(a["stream"] for a in data["activities"])
    if set(per_stream.values()) != {3}:
        errors.append("each stream must have exactly three activities")
    # the scorecard rules average practices and functions as plain sums
    if set(Counter(s["practice"] for s in data["streams"]).values()) != {2}:
        errors.append("each practice must have exactly two streams")
    per_function = Counter(p["function"] for p in data["security_practices"])
    if set(per_function.values()) != {3}:
        errors.append("each business function must have exactly three practices")
    if errors:
        sys.exit("invalid SAMM model:\n  " + "\n  ".join(errors))


def build(data: dict[str, list[dict]]) -> dict:
    functions = sorted(data["business_functions"], key=lambda f: f["order"])
    maturity_number = {m["id"]: m["number"] for m in data["maturity_levels"]}
    # activities point to a practice level, which points to a maturity level
    levels = {
        pl["id"]: maturity_number[pl["maturityLevel"]] for pl in data["practice_levels"]
    }
    answer_sets = by_id(data["answer_sets"])
    question_of = {q["activity"]: q for q in data["questions"]}

    practices_of = defaultdict(list)
    for practice in data["security_practices"]:
        practices_of[practice["function"]].append(practice)
    streams_of = defaultdict(list)
    for stream in data["streams"]:
        streams_of[stream["practice"]].append(stream)
    activities_of = defaultdict(list)
    for activity in data["activities"]:
        activities_of[activity["stream"]].append(activity)
    objectives_of = defaultdict(dict)
    for practice_level in data["practice_levels"]:
        objectives_of[practice_level["practice"]][levels[practice_level["id"]]] = text(
            practice_level["objective"]
        )

    nodes = []
    # (function code, name, [(practice code, name, stream count)])
    scorecard = []

    def add(ref_id: str, depth: int, parent: str | None, **fields) -> str:
        urn = f"{URN_NODE}:{ref_id.lower()}"
        node = {"urn": urn, "assessable": False, "depth": depth}
        if parent:
            node["parent_urn"] = parent
        node["ref_id"] = ref_id
        node.update({k: v for k, v in fields.items() if v})
        nodes.append(node)
        return urn

    for function in functions:
        code = FUNCTION_CODES[function["name"]]
        function_urn = add(
            code,
            1,
            None,
            name=function["name"],
            description=text(function["description"]),
        )
        scorecard.append((code, function["name"], []))
        for practice in sorted(practices_of[function["id"]], key=lambda p: p["order"]):
            practice_code = f"{code}-{practice['shortName']}"
            scorecard[-1][2].append(
                (practice_code, practice["name"], len(streams_of[practice["id"]]))
            )
            objectives = objectives_of[practice["id"]]
            description = "\n\n".join(
                [text(practice["longDescription"])]
                + [f"Level {n} objective: {objectives[n]}" for n in sorted(objectives)]
            )
            practice_urn = add(
                practice_code,
                2,
                function_urn,
                name=practice["name"],
                description=description,
            )
            for stream in sorted(streams_of[practice["id"]], key=lambda s: s["order"]):
                stream_code = f"{practice_code}-{stream['letter']}"
                stream_urn = add(
                    stream_code,
                    3,
                    practice_urn,
                    name=text(stream["name"]),
                    description=text(stream["description"]),
                )
                for activity in sorted(
                    activities_of[stream["id"]], key=lambda a: levels[a["level"]]
                ):
                    level = levels[activity["level"]]
                    activity_code = f"{practice_code}-{level}-{stream['letter']}"
                    urn = add(
                        activity_code,
                        4,
                        stream_urn,
                        name=text(activity["title"]),
                        description=f"{text(activity['shortDescription'])}\n\n"
                        f"{text(activity['longDescription'])}",
                        annotation=f"Benefit: {text(activity['benefit'])}",
                    )
                    node = nodes[-1]
                    node["assessable"] = True
                    node["implementation_groups"] = [str(n) for n in range(level, 4)]
                    question = question_of[activity["id"]]
                    if quality := question.get("quality"):
                        node["typical_evidence"] = "\n".join(
                            f"- {text(item)}" for item in quality
                        )
                    node["questions"] = {
                        f"{urn}:question:1": build_question(
                            f"{urn}:question:1",
                            question,
                            answer_sets[question["answerSet"]],
                        )
                    }

    maturity = {m["number"]: text(m["description"]) for m in data["maturity_levels"]}
    framework_urn = f"{URN_PREFIX}:framework:{LIBRARY_ID}"
    return {
        "urn": f"{URN_PREFIX}:library:{LIBRARY_ID}",
        "locale": "en",
        "ref_id": "OWASP-SAMM-2.2",
        "name": "OWASP SAMM v2.2",
        "description": DESCRIPTION,
        "copyright": "CC BY-SA 4.0 - The OWASP Foundation",
        "version": VERSION,
        "publication_date": PUBLICATION_DATE,
        "provider": "OWASP",
        "packager": "intuitem",
        "objects": {
            "framework": {
                "urn": framework_urn,
                "ref_id": "OWASP-SAMM-2.2",
                "name": "OWASP SAMM v2.2",
                "description": DESCRIPTION,
                "min_score": 0,
                "max_score": 4,
                "field_visibility": {k: dict(v) for k, v in FIELD_VISIBILITY.items()},
                "scores_definition": SCORES_DEFINITION,
                "implementation_groups_definition": [
                    {
                        "ref_id": str(n),
                        "name": f"Target maturity level {n}",
                        "description": maturity[n],
                    }
                    for n in sorted(maturity)
                ],
                "outcomes_definition": build_scorecard(
                    scorecard, top_group=str(max(maturity))
                ),
                "requirement_nodes": nodes,
            }
        },
    }


def samm_sum(subset: str, divisor: int) -> str:
    """CEL for the sum of a subset's scores, as SAMM points, over `divisor`."""
    return (
        f"{subset}.scored_count > 0 ? {subset}.implementation_score"
        f" * double({subset}.scored_count) / {float(SCALE * divisor)} : 0.0"
    )


def build_scorecard(scorecard: list, top_group: str) -> list[dict]:
    """Number rules for the SAMM scorecard, overall first, then each function
    followed by its practices. Practices and functions have equal sizes (see
    validate), so a mean of practices is the sum over all their streams. Every
    activity is in the top target level, so that group is the whole scope."""
    practice_streams = [n for _, _, practices in scorecard for _, _, n in practices]
    rules = [
        {
            "ref_id": "overall",
            "label": "Overall SAMM score",
            "kind": "number",
            "expression": samm_sum(f'groups["{top_group}"]', sum(practice_streams)),
        }
    ]
    for code, name, practices in scorecard:
        rules.append(
            {
                "ref_id": code.lower(),
                "label": f"{code} · {name}",
                "kind": "number",
                "expression": samm_sum(
                    f'sections["{code.lower()}"]', sum(n for _, _, n in practices)
                ),
            }
        )
        for practice_code, practice_name, streams in practices:
            rules.append(
                {
                    "ref_id": practice_code.lower().replace("-", "_"),
                    "label": f"{practice_code} · {practice_name}",
                    "kind": "number",
                    "expression": samm_sum(
                        f'sections["{practice_code.lower()}"]', streams
                    ),
                }
            )
    return rules


def build_question(urn: str, question: dict, answer_set: dict) -> dict:
    choices = []
    for index, answer in enumerate(
        sorted(answer_set["values"], key=lambda v: v["order"]), start=1
    ):
        add_score, compute_result = ANSWER_SCORING[answer["value"]]
        choices.append(
            {
                "urn": f"{urn}:choice:{index}",
                "value": text(answer["text"]),
                "add_score": add_score,
                "compute_result": compute_result,
            }
        )
    return {"type": "unique_choice", "text": text(question["text"]), "choices": choices}


def _str_representer(dumper, data):
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the OWASP SAMM library.")
    parser.add_argument("--source", type=Path, help="extracted owaspsamm/core checkout")
    parser.add_argument("--output-dir", type=Path, default=LIBRARIES)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        source = args.source or fetch(Path(tmp))
        data = load(source)
    validate(data)
    library = build(data)
    yaml.add_representer(str, _str_representer)
    path = args.output_dir / f"{LIBRARY_ID}.yaml"
    path.write_text(
        yaml.dump(library, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
