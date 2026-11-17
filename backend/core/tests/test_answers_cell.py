"""Tests for render_answers_cell() / parse_answers_cell(), the `answers` column
shared by the audit CSV and XLSX exports and by the data wizard import.

These operate on plain dicts (the shape build_questions_dict/build_answers_dict
return), so none of them need the database.
"""

from core.utils import parse_answers_cell, render_answers_cell, visible_questions

Q_TEXT = "urn:test:q:text"
Q_SINGLE = "urn:test:q:single"
Q_MULTI = "urn:test:q:multi"

C_RED = "urn:test:choice:red"
C_BLUE = "urn:test:choice:blue"
C_A = "urn:test:choice:a"
C_B = "urn:test:choice:b"


def questions():
    return {
        Q_TEXT: {"type": "text", "text": "Describe the control"},
        Q_SINGLE: {
            "type": "unique_choice",
            "text": "Pick one colour",
            "choices": [
                {
                    "urn": C_RED,
                    "value": "Red",
                    "translations": {"fr": {"value": "Rouge"}},
                },
                {
                    "urn": C_BLUE,
                    "value": "Blue",
                    "translations": {"fr": {"value": "Bleu"}},
                },
            ],
        },
        Q_MULTI: {
            "type": "multiple_choice",
            "text": "Pick any",
            "choices": [
                {"urn": C_A, "value": "Alpha"},
                {"urn": C_B, "value": "Beta"},
            ],
        },
    }


def roundtrip(answers, qdict=None):
    qdict = qdict or questions()
    parsed, warnings = parse_answers_cell(render_answers_cell(qdict, answers), qdict)
    return parsed, warnings


class TestRender:
    def test_every_line_starts_with_the_question_urn(self):
        cell = render_answers_cell(questions(), {Q_SINGLE: C_RED})
        for block in cell.split("\n\n"):
            assert block.startswith("[urn:test:q:")

    def test_unanswered_questions_get_a_hint(self):
        cell = render_answers_cell(questions(), {})
        assert f"[{Q_TEXT}] Describe the control >> [free text]" in cell
        assert f"[{Q_SINGLE}] Pick one colour >> [Red / Blue]" in cell
        assert f"[{Q_MULTI}] Pick any (multiple) >> [Alpha / Beta]" in cell

    def test_questions_keep_their_definition_order(self):
        cell = render_answers_cell(questions(), {})
        assert [b.split("]")[0][1:] for b in cell.split("\n\n")] == [
            Q_TEXT,
            Q_SINGLE,
            Q_MULTI,
        ]

    def test_no_questions_renders_empty(self):
        assert render_answers_cell(None, {}) == ""
        assert render_answers_cell({}, {}) == ""

    def test_hidden_question_is_omitted(self):
        qdict = questions()
        qdict[Q_MULTI]["depends_on"] = {
            "question": Q_SINGLE,
            "answers": [C_RED],
            "condition": "any",
        }
        # Q_SINGLE answered "Blue", so the dependent question does not apply.
        cell = render_answers_cell(qdict, {Q_SINGLE: C_BLUE})
        assert Q_MULTI not in cell
        # Answered "Red" and it comes back.
        assert Q_MULTI in render_answers_cell(qdict, {Q_SINGLE: C_RED})


class TestRoundTrip:
    def test_text_single_and_multiple_choice(self):
        answers = {Q_TEXT: "We encrypt at rest", Q_SINGLE: C_RED, Q_MULTI: [C_A, C_B]}
        parsed, warnings = roundtrip(answers)
        assert parsed == answers
        assert warnings == []

    def test_multi_line_text_answer_survives(self):
        # The bug this guards: the exporter joins blocks with a blank line, so a
        # parser splitting on "\n" kept only the first line of this answer.
        answer = "First line\nSecond line\n\nFourth line"
        parsed, warnings = roundtrip({Q_TEXT: answer})
        assert parsed[Q_TEXT] == answer
        assert warnings == []

    def test_answer_containing_the_separator_survives(self):
        parsed, _ = roundtrip({Q_TEXT: "a >> b"})
        assert parsed[Q_TEXT] == "a >> b"

    def test_untouched_export_changes_nothing(self):
        cell = render_answers_cell(questions(), {})
        parsed, warnings = parse_answers_cell(cell, questions())
        assert parsed == {}
        assert warnings == []


class TestParse:
    def test_emptied_answer_clears_it(self):
        parsed, warnings = parse_answers_cell(
            f"[{Q_TEXT}] Describe the control >>", questions()
        )
        assert parsed == {Q_TEXT: None}
        assert warnings == []

    def test_choice_matched_across_languages(self):
        # Exported while the UI was in French, re-imported in English.
        parsed, warnings = parse_answers_cell(
            f"[{Q_SINGLE}] Choisissez une couleur >> Rouge", questions()
        )
        assert parsed == {Q_SINGLE: C_RED}
        assert warnings == []

    def test_unknown_choice_warns_and_leaves_the_answer_alone(self):
        parsed, warnings = parse_answers_cell(
            f"[{Q_SINGLE}] Pick one colour >> Purple", questions()
        )
        assert parsed == {}
        assert len(warnings) == 1
        assert "Purple" in warnings[0]

    def test_partially_unknown_multiple_choice_keeps_what_matched(self):
        parsed, warnings = parse_answers_cell(
            f"[{Q_MULTI}] Pick any >> Alpha | Gamma", questions()
        )
        assert parsed == {Q_MULTI: [C_A]}
        assert len(warnings) == 1
        assert "Gamma" in warnings[0]

    def test_unknown_question_urn_warns(self):
        parsed, warnings = parse_answers_cell(
            "[urn:test:q:gone] Removed question >> Red", questions()
        )
        assert parsed == {}
        assert len(warnings) == 1
        assert "urn:test:q:gone" in warnings[0]

    def test_empty_cell(self):
        assert parse_answers_cell(None, questions()) == ({}, [])
        assert parse_answers_cell("", questions()) == ({}, [])


class TestLegacyCells:
    """Workbooks exported before answer lines carried the question URN."""

    def test_matched_on_question_text(self):
        cell = (
            "Describe the control >> We encrypt at rest\n\n"
            "Pick one colour >> Red\n\n"
            "Pick any (multiple) >> Alpha | Beta"
        )
        parsed, warnings = parse_answers_cell(cell, questions())
        assert parsed == {
            Q_TEXT: "We encrypt at rest",
            Q_SINGLE: C_RED,
            Q_MULTI: [C_A, C_B],
        }
        assert warnings == []

    def test_unmatched_text_warns(self):
        parsed, warnings = parse_answers_cell("Old question >> Red", questions())
        assert parsed == {}
        assert len(warnings) == 1
        assert "Old question" in warnings[0]

    def test_hints_still_skipped(self):
        parsed, warnings = parse_answers_cell(
            "Describe the control >> [free text]", questions()
        )
        assert parsed == {}
        assert warnings == []


class TestVisibleQuestions:
    def test_chain_hidden_when_parent_hidden(self):
        qdict = questions()
        qdict[Q_MULTI]["depends_on"] = {
            "question": Q_SINGLE,
            "answers": [C_RED],
            "condition": "any",
        }
        qdict[Q_TEXT]["depends_on"] = {
            "question": Q_MULTI,
            "answers": [C_A],
            "condition": "any",
        }
        # Q_SINGLE unanswered hides Q_MULTI, which hides Q_TEXT.
        assert visible_questions(qdict, {}) == {
            Q_SINGLE: {**qdict[Q_SINGLE], "urn": Q_SINGLE}
        }

    def test_no_depends_on_keeps_everything(self):
        assert list(visible_questions(questions(), {})) == [Q_TEXT, Q_SINGLE, Q_MULTI]
