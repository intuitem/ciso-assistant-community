import pytest


@pytest.fixture(autouse=True)
def recompute_requests(monkeypatch):
    """The recompute jobs asked for, recorded instead of queued: nothing a
    test does lands in the task queue's storage, and a test runs the job
    itself (metrology.recompute.compute_marked_formulas) when it needs one."""
    from metrology import recompute

    requests = []
    monkeypatch.setattr(recompute, "request_recompute", lambda: requests.append(1))
    return requests
