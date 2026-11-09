from backend.genie import GenieClient

SPACES = {"demand": "S1", "manufacturing": "S2"}


class FakeHttp:
    """Scripted Genie REST responses keyed by (method, path-suffix)."""

    def __init__(self, message_states, attachments=None, query_result=None, error=None):
        self.states = list(message_states)
        self.attachments, self.query_result, self.error = attachments or [], query_result, error
        self.calls = []

    def __call__(self, method, path, body=None, token=None):
        self.calls.append((method, path, token))
        if path.endswith("/start-conversation"):
            return {"conversation_id": "c1", "message_id": "m1"}
        if path.endswith("/messages") and method == "POST":
            return {"id": "m2", "message_id": "m2"}
        if "/query-result" in path:
            return self.query_result
        state = self.states.pop(0) if len(self.states) > 1 else self.states[0]
        msg = {"status": state, "attachments": self.attachments if state == "COMPLETED" else []}
        if state == "FAILED":
            msg["error"] = {"error": self.error or "boom"}
        return msg


def gc(http, timeout_s=60):
    clock = {"t": 0.0}

    def sleep(s):
        clock["t"] += s
    return GenieClient(SPACES, http=http, sleep=sleep, clock=lambda: clock["t"], timeout_s=timeout_s)


def test_genie_text_only_and_failure():
    # text-only answer (e.g. from the knowledge PDF): ok, no SQL
    http = FakeHttp(["EXECUTING_QUERY", "COMPLETED"], attachments=[{"text": {"content": "Un lancio è pronto quando..."}}])
    r = gc(http).ask("Cosa rende un lancio pronto?", "demand", user_token="u")
    assert r["status"] == "ok" and r["sql"] is None and "pronto" in r["text"] and r["conversation_id"] == "c1"
    assert all(tok == "u" for _, _, tok in http.calls)
    # FAILED: error status with message, no exception
    r = gc(FakeHttp(["FAILED"], error="table not found")).ask("x", "demand")
    assert r["status"] == "error" and "table not found" in r["text"]
    # timeout after 60 s: error status, no exception
    r = gc(FakeHttp(["EXECUTING_QUERY"]), timeout_s=60).ask("x", "demand")
    assert r["status"] == "error" and "longer" in r["text"].lower()


def test_genie_query_attachment_returns_rows():
    att = [{"attachment_id": "a1", "query": {"query": "SELECT brand", "description": "Zyvanta is at risk"}}]
    qr = {"statement_response": {"manifest": {"schema": {"columns": [{"name": "brand"}]}},
                                 "result": {"data_array": [["Zyvanta"]]}}}
    r = gc(FakeHttp(["COMPLETED"], attachments=att, query_result=qr)).ask("q", "manufacturing")
    assert r["status"] == "ok" and r["sql"] == "SELECT brand" and r["columns"] == ["brand"] and r["rows"] == [["Zyvanta"]]


def test_genie_no_data_status_when_query_returns_zero_rows():
    att = [{"attachment_id": "a1", "query": {"query": "SELECT 1 WHERE false"}}]
    qr = {"statement_response": {"manifest": {"schema": {"columns": [{"name": "x"}]}}, "result": {}}}
    r = gc(FakeHttp(["COMPLETED"], attachments=att, query_result=qr)).ask("q", "demand")
    assert r["status"] == "no_data"


def test_genie_follow_up_uses_conversation():
    http = FakeHttp(["COMPLETED"], attachments=[{"text": {"content": "ok"}}])
    gc(http).ask("and OEE?", "manufacturing", conversation_id="c9")
    assert any(m == "POST" and p.endswith("/spaces/S2/conversations/c9/messages") for m, p, _ in http.calls)
