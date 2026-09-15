#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

ARG_RE = re.compile(r"^\s*ARG\s+([A-Za-z0-9_]+)\s*=\s*(\S+)", re.I)
FROM_RE = re.compile(r"^\s*FROM\s+(?:--\S+\s+)*(\S+)(?:\s+AS\s+(\S+))?", re.I)
COPY_FROM_RE = re.compile(r"^\s*COPY\s+(?:--\S+\s+)*--from=(\S+)", re.I)
VAR_RE = re.compile(r"\$\{([A-Za-z0-9_]+)\}|\$([A-Za-z0-9_]+)")
REF_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._\-/]*(:[A-Za-z0-9][A-Za-z0-9._\-]*)?(@sha256:[a-f0-9]{64})?$"
)


def resolve(ref, args):
    return VAR_RE.sub(lambda m: args.get(m.group(1) or m.group(2), ""), ref)


def is_image(ref, stages):
    return ref.lower() not in stages and ("/" in ref or ":" in ref)


def extract(path):
    args, stages, refs = {}, set(), []
    for line in Path(path).read_text().splitlines():
        m = ARG_RE.match(line)
        if m:
            args[m.group(1)] = m.group(2).strip("\"'")
            continue
        m = FROM_RE.match(line)
        if m:
            ref = resolve(m.group(1), args)
            if is_image(ref, stages):
                refs.append(ref)
            if m.group(2):
                stages.add(m.group(2).lower())
            continue
        m = COPY_FROM_RE.match(line)
        if m:
            ref = resolve(m.group(1), args)
            if is_image(ref, stages):
                refs.append(ref)
    return refs


def main(argv):
    as_json = "--json" in argv
    paths = [a for a in argv if not a.startswith("--")]
    seen, rejected = [], []
    for path in paths:
        for ref in extract(path):
            if not REF_RE.match(ref):
                rejected.append((path, ref))
            elif ref not in seen:
                seen.append(ref)
    if rejected:
        for path, ref in rejected:
            print(f"{path}: not a valid image reference: {ref!r}", file=sys.stderr)
        return 1
    seen.sort()
    print(json.dumps(seen) if as_json else "\n".join(seen))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
