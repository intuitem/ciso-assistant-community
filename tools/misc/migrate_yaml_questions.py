#!/usr/bin/env python3

"""
This script processes a YAML file to transform its structure.
Specifically, it looks for the "question" key, which contains "question_type," "questions," 
and optionally "question_choices," and converts it into a new format under the "questions" key.

- If the original format includes multiple questions, they are extracted and restructured.
- Choices (if present) are also converted accordingly.
- The script ensures that only the required modifications are made without altering other YAML elements.

Usage:
    python script.py input.yaml
"""

import sys
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

def convert_question_format(data):
    """
    Recursively traverses the YAML structure and, if a "question" key 
    (containing "question_type," "questions," and optionally "question_choices") is found, 
    it is transformed into the target "questions" format.

    Returns True if the conversion was performed.
    """
    changed = False
    if isinstance(data, dict):
        if "question" in data and isinstance(data["question"], dict):
            q = data["question"]
            if "question_type" in q and "questions" in q:
                new_questions = CommentedMap()
                q_type = q["question_type"]
                # Retrieve choices if they exist (only for non-text/date types)
                choices = q.get("question_choices", None)
                question_list = q["questions"]
                if isinstance(question_list, list):
                    for question in question_list:
                        if isinstance(question, dict) and "urn" in question and "text" in question:
                            q_urn = question["urn"]
                            new_question_entry = CommentedMap()
                            new_question_entry["type"] = q_type
                            new_question_entry["text"] = question["text"]
                            if choices is not None and isinstance(choices, list):
                                new_choices = []
                                for idx, choice_value in enumerate(choices, start=1):
                                    new_choice = CommentedMap()
                                    new_choice["urn"] = f"{q_urn}:choice:{idx}"
                                    new_choice["value"] = choice_value
                                    new_choices.append(new_choice)
                                new_question_entry["choices"] = new_choices
                            new_questions[q_urn] = new_question_entry
                data["questions"] = new_questions
                del data["question"]
                changed = True
    return changed

def process_file(filename):
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = yaml.load(f)
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return

    if data is None:
        return

    conversion_happened = convert_question_format(data)

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            yaml.dump(data, f)
        if conversion_happened:
            print(f"File processed: {filename}")
        else:
            print(f"No conversion necessary in: {filename}")
    except Exception as e:
        print(f"Error writing to {filename}: {e}")

def main():
    if len(sys.argv) != 2:
        print("Usage: {} <yaml_file>".format(sys.argv[0]))
        sys.exit(1)
    filename = sys.argv[1]
    process_file(filename)

if __name__ == "__main__":
    main()
