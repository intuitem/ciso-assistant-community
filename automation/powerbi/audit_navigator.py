"""Check that the connector's navigator only ever grew at the end.

Reports built with connector <= 1.0.1 navigate by position (`Source{0}[Data]`)
because the navigator declared no key before 1.0.2. For those, inserting or
reordering an entry in Facts / Dimensions / Bridges silently repoints a query
at a different table — same shape, wrong data, no error. New entries therefore
have to be appended to the end of their group, and that cohort never expires,
so this is permanent discipline rather than a migration.

Usage: python automation/powerbi/audit_navigator.py [baseline-ref]
"""

import pathlib
import re
import subprocess
import sys

PQ_PATH = "automation/powerbi/connector/CisoAssistant.pq"
GROUPS = ("facts", "dimensions", "bridges")


def navigator_entries(source):
    entries = {}
    for group in GROUPS:
        block = re.search(rf"{group} = #table\((.*?)\n        \)", source, re.S)
        if not block:
            raise SystemExit(f"{group}: navigator group not found")
        entries[group] = re.findall(r'\{ "([^"]+)", Get', block.group(1))
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
