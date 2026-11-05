import re

# Django template tags a PDF layout never legitimately needs. Rejected at upload
# (and skipped at render) as defense-in-depth: under the DTL engine these are not
# an RCE vector, but they allow tag-library / template inclusion and context
# disclosure — unnecessary surface for a document layout.
FORBIDDEN_TEMPLATE_TAGS = ("load", "include", "extends", "debug", "ssi")
_FORBIDDEN_RE = re.compile(r"{%\s*(" + "|".join(FORBIDDEN_TEMPLATE_TAGS) + r")\b")


def find_forbidden_template_tags(source: str) -> list[str]:
    """Return the sorted set of forbidden template tags found in the source."""
    return sorted({m.group(1) for m in _FORBIDDEN_RE.finditer(source or "")})
