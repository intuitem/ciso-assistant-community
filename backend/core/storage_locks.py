"""One transaction-scoped lock per stored file name.

Cleanup and any writer that points a new row at an existing name must both
call `lock_stored_name` inside `transaction.atomic` and hold it until commit.
"""

import hashlib

from django.core.files.storage import default_storage
from django.db import connection
from django.db.transaction import TransactionManagementError


def _lock_key(name):
    """Stable signed 64-bit key. Python's hash() changes per process."""
    storage_class = (
        f"{type(default_storage).__module__}.{type(default_storage).__qualname__}"
    )
    digest = hashlib.sha256(f"{storage_class}\0{name}".encode()).digest()
    return int.from_bytes(digest[:8], "big", signed=True)


def lock_stored_name(name):
    """Hold the lock for `name` until this transaction ends.

    On PostgreSQL this is `pg_advisory_xact_lock` for the storage class plus
    `name`. A cleanup that takes it, checks references, and deletes the blob
    cannot interleave with a writer that takes it before inserting a row for
    that name. The lock releases on commit or rollback.

    On SQLite this does nothing. SQLite allows one writer at a time and holds
    that write lock for the whole transaction, so another connection cannot
    commit a new reference while this transaction is open.
    """
    if not name:
        return
    if not connection.in_atomic_block:
        raise TransactionManagementError(
            "lock_stored_name() must be called inside a transaction."
        )
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [_lock_key(name)])
        # The lock is held by the transaction, not by the cursor result.
        cursor.fetchone()
