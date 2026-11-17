"""Check that the connector's navigator only ever grew at the end.

Reports built with connector <= 1.0.1 navigate by position, so a moved entry
silently repoints their queries at another table.

Usage: python automation/powerbi/audit_navigator.py [baseline-ref]
"""

import pathlib
import re
import subprocess
import sys

PQ_PATH = "automation/powerbi/connector/CisoAssistant.pq"
GROUPS = ("facts", "dimensions", "bridges")


# Matched on row shape, not the data expression: an unrecognised row would
# shorten the list. The unquoted second element excludes the column header.
ROW = re.compile(r'\{ "([^"]+)",\s*[^"\s]')
ROW_LINE = re.compile(r'^\s*\{ "')
HEADER_LINE = re.compile(r'^\s*\{ "Name", "Data"')


def navigator_entries(source):
    entries = {}
    for group in GROUPS:
        block = re.search(rf"{group} = #table\((.*?)\n        \)", source, re.S)
        if not block:
            raise SystemExit(f"{group}: navigator group not found")
        body = block.group(1)
        names = ROW.findall(body)
        rows = [
            line
            for line in body.splitlines()
            if ROW_LINE.match(line) and not HEADER_LINE.match(line)
        ]
        if len(names) != len(rows):
            raise SystemExit(
                f"{group}: matched {len(names)} names in {len(rows)} rows — the "
                f"row shape changed, update this script before trusting it"
            )
        entries[group] = names
    return entries


def baseline_source(ref):
    result = subprocess.run(
        ["git", "show", f"{ref}:{PQ_PATH}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def main():
    ref = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    source = baseline_source(ref)
    if source is None:
        print(f"navigator: no baseline at {ref}, nothing to compare")
        return 0

    before = navigator_entries(source)
    after = navigator_entries(pathlib.Path(PQ_PATH).read_text())

    failures = []
    for group in GROUPS:
        old, new = before[group], after[group]
        if new[: len(old)] != old:
            failures.append(
                f"  {group}: order changed\n    was: {old}\n    now: {new[: len(old)]}"
            )
        else:
            added = new[len(old) :]
            print(
                f"navigator: {group} {len(old)} -> {len(new)}"
                + (f", added {added}" if added else "")
            )

    if failures:
        print(
            f"\nnavigator entries must only be appended (baseline {ref}):",
            file=sys.stderr,
        )
        print("\n".join(failures), file=sys.stderr)
        print(
            "\nReports built on connector <= 1.0.1 bind to positions; moving an\n"
            "entry repoints their queries at another table.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
