import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "convert_library_v2.py"
SPEC = importlib.util.spec_from_file_location("convert_library_v2", SCRIPT_PATH)
convert_library_v2 = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(convert_library_v2)


ANSWERS = {
    "TF": {
        "type": "unique_choice",
        "choices": [{"urn": "", "value": "True"}],
    },
}


def test_inject_questions_references_global_groups_and_keeps_local_order():
    node = {"urn": "urn:intuitem:risk:req_node:test:a1.a"}
    convert_library_v2.inject_questions_into_node(
        {
            "questions": "Not achieved one\nNot achieved two\nAchieved one",
            "answer": "TF\nTF\nTF",
            "question_groups": "not_achieved\nnot_achieved\nachieved",
            "question_groups_order": "not_achieved\nachieved",
        },
        node,
        ANSWERS,
        question_group_ids={"not_achieved", "achieved"},
    )

    question_urns = list(node["questions"])
    assert [node["questions"][urn]["question_group"] for urn in question_urns] == [
        "not_achieved",
        "not_achieved",
        "achieved",
    ]
    assert node["questions_properties"] == {
        "groups_order": ["not_achieved", "achieved"]
    }


@pytest.mark.parametrize(
    ("groups", "group_order", "known_ids", "message"),
    [
        ("not_achieved\nachieved", "not_achieved", {"not_achieved", "achieved"}, "missing group IDs"),
        (
            "not_achieved\nachieved",
            "not_achieved\nachieved\nachieved",
            {"not_achieved", "achieved"},
            "Duplicate group ID",
        ),
        ("not_achieved\nunknown", "not_achieved\nunknown", {"not_achieved"}, "Unknown question group IDs"),
    ],
)
def test_inject_questions_rejects_inconsistent_group_metadata(
    groups, group_order, known_ids, message
):
    node = {"urn": "urn:intuitem:risk:req_node:test:a1.a"}
    with pytest.raises(ValueError, match=message):
        convert_library_v2.inject_questions_into_node(
            {
                "questions": "One\nTwo",
                "answer": "TF\nTF",
                "question_groups": groups,
                "question_groups_order": group_order,
            },
            node,
            ANSWERS,
            question_group_ids=known_ids,
        )
