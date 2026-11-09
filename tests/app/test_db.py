from backend.db import ACTION_INSERT_SQL, CredentialCache


def test_connection_refreshes_expired_credential():
    clock = {"t": 1000.0}
    issued = []

    def fetch():
        issued.append(clock["t"])
        return f"tok{len(issued)}", clock["t"] + 3600

    cache = CredentialCache(fetch, clock=lambda: clock["t"], margin_s=300)
    assert cache.get() == "tok1"
    clock["t"] += 3000           # still > 5 min before expiry
    assert cache.get() == "tok1"
    clock["t"] += 400            # within the 5-minute margin -> refresh
    assert cache.get() == "tok2" and len(issued) == 2


def test_action_insert_is_conflict_safe():
    assert "ON CONFLICT (launch_id, action_type) WHERE status = 'open' DO NOTHING" in ACTION_INSERT_SQL
    assert "RETURNING" in ACTION_INSERT_SQL


def test_expiry_to_epoch_handles_sdk_types():
    from datetime import datetime, timezone
    from backend.db import to_epoch

    class SdkTimestamp:  # databricks-sdk returns its own Timestamp type
        def ToDatetime(self):
            return datetime(2026, 9, 22, 10, 0, tzinfo=timezone.utc)

    want = datetime(2026, 9, 22, 10, 0, tzinfo=timezone.utc).timestamp()
    assert to_epoch("2026-09-22T10:00:00Z", now=0) == want
    assert to_epoch(datetime(2026, 9, 22, 10, 0, tzinfo=timezone.utc), now=0) == want
    assert to_epoch(SdkTimestamp(), now=0) == want
    assert to_epoch(None, now=100) == 3700
