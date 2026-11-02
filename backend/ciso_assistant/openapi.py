import inspect
from collections import Counter, defaultdict

from drf_spectacular.contrib.knox_auth_token import KnoxTokenScheme
from drf_spectacular.openapi import AutoSchema as BaseAutoSchema

HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
# Namespaces above this many operations get one page per sub-resource.
MAX_NAMESPACE_OPERATIONS = 50
# Labels from frontend/messages/en.json where the slug reads badly.
PAGE_TITLES = {
    "agg_data": "Aggregated data",
    "build": "Build info",
    "crq": "Cyber Risk Quantification",
    "csrf": "CSRF",
    "cwes": "CWEs",
    "ebios-rm": "EBIOS RM",
    "ebios-rm/ro-to": "RO/TO couples",
    "iam": "IAM",
    "idp-groups": "IdP groups",
    "pmbok": "PMBOK",
    "privacy/dpia-requirement-changes": "DPIA requirement changes",
    "resilience/dora-incident-reports": "DORA incident reports",
    "scim": "SCIM",
    "serdes": "Backup and restore",
    "ttp-catalogs": "TTP catalogs",
}


class AutoSchema(BaseAutoSchema):
    def get_description(self):
        # Only docstrings written on the endpoint's own class are public docs;
        # inherited ones (base viewsets, mixins) are implementation notes.
        view_class = type(self.view)
        action = getattr(self.view, "action", None) or self.method.lower()
        action_doc = (
            inspect.getdoc(getattr(self.view, action))
            if action in vars(view_class)
            else None
        )
        return inspect.cleandoc(action_doc or vars(view_class).get("__doc__") or "")


class PersonalAccessTokenScheme(KnoxTokenScheme):
    priority = 1
    name = "PersonalAccessToken"

    def get_security_definition(self, auto_schema):
        return {
            **super().get_security_definition(auto_schema),
            "description": "Personal access token, created from your user profile. Send it as `Authorization: Token <PAT>`.",
        }


def _title(slug: str) -> str:
    if slug in PAGE_TITLES:
        return PAGE_TITLES[slug]
    slug = slug.rpartition("/")[2].removeprefix("get_")
    return slug.replace("-", " ").replace("_", " ").capitalize()


def split_namespace_tags(result, generator, request, public):
    """Tag operations for one doc page per resource (GitBook builds pages from tags).

    A large first path segment that is never followed directly by a path
    parameter (e.g. /api/ebios-rm/studies/) is a namespace: its operations are
    re-tagged "<namespace>/<resource>" and nested under it with x-parent.
    """
    operations = []
    for path, item in result.get("paths", {}).items():
        segments = path.removeprefix("/api/").strip("/").split("/")
        for method, operation in item.items():
            if method in HTTP_METHODS:
                operations.append((segments, operation))

    sizes = Counter(segments[0] for segments, _ in operations)
    resources = {
        segments[0]
        for segments, _ in operations
        if len(segments) == 1 or segments[1].startswith("{")
    }
    namespaces = {
        name
        for name, size in sizes.items()
        if name not in resources and size > MAX_NAMESPACE_OPERATIONS
    }

    children = defaultdict(set)
    for segments, operation in operations:
        if segments[0] in namespaces and operation.get("tags") == [segments[0]]:
            operation["tags"] = [f"{segments[0]}/{segments[1]}"]
            children[segments[0]].add(segments[1])

    tags = {tag for _, operation in operations for tag in operation.get("tags", [])}
    result["tags"] = []
    for name in sorted(tags | set(children)):
        parent, _, child = name.partition("/")
        entry = {"name": name, "x-page-title": _title(name)}
        if child:
            entry["x-parent"] = parent
        result["tags"].append(entry)
    return result
