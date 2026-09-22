import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "convert_library_v2.py"
SPEC = importlib.util.spec_from_file_location("convert_library_v2", SCRIPT_PATH)
convert_library_v2 = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(convert_library_v2)


ANSWERS = {
    "TF-NA": {
        "type": "unique_choice",
        "group_description": "Not Achieved",
        "choices": [{"urn": "", "value": "True"}],
    },
    "TF-A": {
        "type": "unique_choice",
        "group_description": "Achieved",
        "choices": [{"urn": "", "value": "True"}],
    },
}


def test_inject_questions_builds_presentation_groups_without_changing_questions():
    node = {"urn": "urn:intuitem:risk:req_node:test:a1.a"}
    convert_library_v2.inject_questions_into_node(
        {
            "questions": "NA one\nNA two\nA one",
            "answer": "TF-NA\nTF-NA\nTF-A",
            "answer_group_order": "TF-NA\nTF-A",
        },
        node,
        ANSWERS,
    )

    question_urns = list(node["questions"])
    assert node["questions_properties"] == {
        "groups": {
            1: {
                "description": "Not Achieved",
                "order": question_urns[:2],
            },
            2: {"description": "Achieved", "order": question_urns[2:]},
        }
    }


@pytest.mark.parametrize(
    "group_order, message",
    [
        ("TF-NA", "missing answer IDs"),
        ("TF-NA\nTF-A\nTF-A", "Duplicate answer ID"),
        ("TF-NA\nTF-PA\nTF-A", "unused answer IDs"),
    ],
)
def test_inject_questions_rejects_inconsistent_group_metadata(group_order, message):
    node = {"urn": "urn:intuitem:risk:req_node:test:a1.a"}
    with pytest.raises(ValueError, match=message):
        convert_library_v2.inject_questions_into_node(
            {
                "questions": "NA one\nA one",
                "answer": "TF-NA\nTF-A",
                "answer_group_order": group_order,
            },
            node,
            ANSWERS,
        )
