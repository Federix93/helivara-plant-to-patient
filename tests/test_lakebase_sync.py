from helivara.lakebase_sync import BOARD, EQUIPMENT, sync_rows, upsert_sql


class FakeCursor:
    def __init__(self, log):
        self.log = log

    def executemany(self, sql, rows):
        self.log.append((sql, list(rows)))

    def execute(self, sql, params=None):
        self.log.append((sql, params))


class FakeConn:
    def __init__(self):
        self.log, self.commits = [], 0

    def cursor(self):
        return FakeCursor(self.log)

    def commit(self):
        self.commits += 1


def test_upsert_sql_is_idempotent():
    sql = upsert_sql("control_tower.launch_risk_board", ["launch_id", "brand", "readiness"], "launch_id")
    assert sql.startswith("INSERT INTO control_tower.launch_risk_board (launch_id, brand, readiness) VALUES (%s, %s, %s)")
    assert "ON CONFLICT (launch_id) DO UPDATE SET brand = EXCLUDED.brand, readiness = EXCLUDED.readiness" in sql
    assert "launch_id = EXCLUDED.launch_id" not in sql


def test_sync_rows_roundtrip_utf8():
    conn = FakeConn()
    sync_rows(conn, "control_tower.launch_risk_board", ["launch_id", "brief_it"], "launch_id",
              [("ZYV-001", "Perché Zyvanta è a rischio? Qualità e priorità")])
    sql, rows = conn.log[0]
    assert rows == [("ZYV-001", "Perché Zyvanta è a rischio? Qualità e priorità")]
    assert conn.commits == 1


def test_sync_rows_returns_count():
    conn = FakeConn()
    assert sync_rows(conn, "t", ["a", "b"], "a", [(1, 2), (3, 4)]) == 2


def test_sync_rows_deletes_rows_no_longer_in_source():
    conn = FakeConn()
    sync_rows(conn, "t", ["a", "b"], "a", [(1, 2)], prune=True)
    assert any("DELETE FROM t WHERE a <> ALL(%s)" in s for s, _ in conn.log)


def test_serving_specs_have_primary_keys():
    assert BOARD["pk"] == "launch_id" and BOARD["pk"] in BOARD["columns"]
    assert EQUIPMENT["pk"] == "equipment" and "failure_prob_30d" in EQUIPMENT["columns"]
