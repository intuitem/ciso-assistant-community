"""Shared helpers for the MCP tool unit tests (mocked HTTP responses)."""

import asyncio
from unittest.mock import Mock

UUID_A = "11111111-1111-1111-1111-111111111111"
UUID_B = "22222222-2222-2222-2222-222222222222"
UUID_C = "33333333-3333-3333-3333-333333333333"
UUID_D = "44444444-4444-4444-4444-444444444444"
UUID_F = "ffffffff-ffff-ffff-ffff-ffffffffffff"


def _response(status_code=200, json_data=None, text=""):
    res = Mock()
    res.status_code = status_code
    res.json.return_value = json_data if json_data is not None else {}
    res.text = text
    return res


def _router(routes):
    calls = []

    def fake(endpoint, params=None, **kwargs):
        calls.append((endpoint, dict(params or {})))
        value = routes.get(endpoint, [])
        if callable(value):
            value = value(params or {})
        return value, None

    fake.calls = calls
    return fake


def run(coro):
    return asyncio.run(coro)
