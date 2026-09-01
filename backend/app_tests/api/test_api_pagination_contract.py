"""Pagination contract, enforced across every registered route.

CI datasets rarely exceed one page, so pagination regressions (routes escaping
the envelope, next links a client cannot resolve, silent fallback on invalid
params) are invisible to per-model tests. These tests sweep the whole router
so any new or modified route stays inside the contract.
"""

import pytest
from django.urls import reverse
from rest_framework import status

from core.models import Threat
from core.urls import router
from iam.models import Folder


def _row_id(row):
    return str(row.get("id")) if isinstance(row, dict) else str(row)


@pytest.mark.django_db
class TestPaginationContract:
    def test_every_route_serves_the_envelope_and_next_links_resolve(
        self, authenticated_client
    ):
        # Guarantee at least one route has a second page.
        root = Folder.get_root_folder()
        for i in range(3):
            Threat.objects.create(name=f"contract-threat-{i}", folder=root)

        followed = 0
        for _, viewset, basename in router.registry:
            url = reverse(f"{basename}-list")
            response = authenticated_client.get(url, {"limit": 1})
            if response.status_code in (
                status.HTTP_405_METHOD_NOT_ALLOWED,
                # Feature-gated route (e.g. idp-groups without SSO configured).
                status.HTTP_403_FORBIDDEN,
            ):
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
        for _, viewset, basename in router.registry:
            url = reverse(f"{basename}-list")
            for params in ({"limit": 0}, {"limit": "abc"}, {"offset": -1}):
                response = authenticated_client.get(url, params)
                if response.status_code in (
                    status.HTTP_405_METHOD_NOT_ALLOWED,
                    status.HTTP_403_FORBIDDEN,
                ):
                    continue
                assert response.status_code == status.HTTP_400_BAD_REQUEST, (
                    basename,
                    params,
                    response.status_code,
                )
