"""Pagination contract, enforced across every registered route.

CI datasets rarely exceed one page, so pagination regressions (routes escaping
the envelope, next links a client cannot resolve, silent fallback on invalid
params) are invisible to per-model tests. These tests sweep every registered
list route — core's router plus the ~15 sub-app routers it includes — so any
new or modified route stays inside the contract.
"""

import pytest
from django.urls import NoReverseMatch, get_resolver, reverse
from rest_framework import status

from core.models import Threat
from iam.models import Folder


def _row_id(row):
    return str(row.get("id")) if isinstance(row, dict) else str(row)


def _list_route_names(resolver=None, prefix=""):
    """Every `-list` route name in the URL conf, namespaces included.

    Walking the resolver rather than one router's registry: list endpoints are
    registered by core's router, by the routers of ebios_rm/privacy/resilience/
    pmbok/metrology/iam/... that core includes, and by standalone ListAPIViews.
    """
    resolver = resolver or get_resolver()
    names = {
        f"{prefix}{name}"
        for name in resolver.reverse_dict
        if isinstance(name, str) and name.endswith("-list")
    }
    for namespace, (_, sub_resolver) in resolver.namespace_dict.items():
        names |= _list_route_names(sub_resolver, f"{prefix}{namespace}:")
    return names


# Routes that are not paginated collections by design.
#   chat-sessions: ChatSessionViewSet.list deliberately answers with a plain
#     array; fe-api/chat/sessions/+server.ts already forwards query params so
#     it can be switched to the envelope later without a frontend change.
#   content-types: a fixed, cached catalogue of Django models, not rows.
#   ...-graph-data: a graph payload keyed by node, not a row collection.
UNPAGINATED_BY_DESIGN = {
    "chat-sessions-list",
    "content-types-list",
    "requirement-mapping-sets-graph-data-list",
}

# Pre-existing breakage, listed rather than silently skipped so it stays
# visible. Neither is caused by, nor in scope for, the pagination work; delete
# an entry once its route is fixed.
#   builtin-metric-samples: 500, BuiltinMetricSample has no FolderMixin so
#     RoleAssignment.get_iam_folder_field raises NotImplementedError.
#   document-attachments: 500, DocumentAttachmentReadSerializer does not exist.
KNOWN_BROKEN = {
    "builtin-metric-samples-list",
    "document-attachments-list",
}

# Reachable, but not with this fixture's session.
SKIPPED_STATUSES = (
    status.HTTP_405_METHOD_NOT_ALLOWED,
    # Feature-gated route (e.g. idp-groups without SSO configured).
    status.HTTP_403_FORBIDDEN,
    # Different auth scheme (SCIM uses its own bearer token).
    status.HTTP_401_UNAUTHORIZED,
)


def _reversible_list_urls():
    """List routes reachable with no URL arguments, as (name, url) pairs.

    Nested lists (``.../<pk>/evidences``) need a parent id, so they cannot be
    swept generically; they are covered by their own per-model tests.
    """
    urls = []
    for name in sorted(_list_route_names()):
        if name in UNPAGINATED_BY_DESIGN or name in KNOWN_BROKEN:
            continue
        try:
            urls.append((name, reverse(name)))
        except NoReverseMatch:
            continue
    return urls


@pytest.mark.django_db
class TestPaginationContract:
    def test_every_route_serves_the_envelope_and_next_links_resolve(
        self, authenticated_client
    ):
        # Guarantee at least one route has a second page.
        root = Folder.get_root_folder()
        for i in range(3):
            Threat.objects.create(name=f"contract-threat-{i}", folder=root)

        swept = _reversible_list_urls()
        # Guard against the sweep silently collapsing to a handful of routes.
        assert len(swept) > 50, len(swept)

        followed = 0
        for basename, url in swept:
            response = authenticated_client.get(url, {"limit": 1})
            if response.status_code in SKIPPED_STATUSES:
                continue
            assert response.status_code == status.HTTP_200_OK, (
                basename,
                response.status_code,
            )
            data = response.data
            assert isinstance(data, dict) and {"count", "next", "results"} <= set(
                data
            ), f"{basename} escapes the pagination envelope"
            assert len(data["results"]) <= 1, basename

            if data["count"] > 1:
                assert data["next"], basename
                # next links must resolve as-is against the API origin: this is
                # what broke the MCP client when the link format drifted.
                next_response = authenticated_client.get(data["next"])
                assert next_response.status_code == status.HTTP_200_OK, (
                    basename,
                    data["next"],
                )
                first_ids = [_row_id(r) for r in data["results"]]
                next_ids = [_row_id(r) for r in next_response.data["results"]]
                # The pk tiebreaker makes consecutive pages disjoint.
                assert next_ids and set(next_ids).isdisjoint(first_ids), basename
                followed += 1

        assert followed >= 1

    def test_invalid_paging_params_are_rejected_on_every_route(
        self, authenticated_client
    ):
        for basename, url in _reversible_list_urls():
            for params in ({"limit": 0}, {"limit": "abc"}, {"offset": -1}):
                response = authenticated_client.get(url, params)
                if response.status_code in SKIPPED_STATUSES:
                    continue
                assert response.status_code == status.HTTP_400_BAD_REQUEST, (
                    basename,
                    params,
                    response.status_code,
                )
