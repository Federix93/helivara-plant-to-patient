from datetime import date

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app


class FakeRepo:
    def __init__(self):
        self.actions, self.calls = [], []

    def list_launches(self):
        return [{"launch_id": "ORB-001", "readiness": 0.9}, {"launch_id": "ZYV-001", "readiness": 0.33}]

    def list_equipment(self, limit):
        return [{"equipment": "L_OSD_001_EQ_01", "failure_prob_30d": 0.94}][:limit]

    def list_actions(self, launch_id=None):
        return [a for a in self.actions if launch_id in (None, a["launch_id"])]

    def create_action(self, payload, created_by):
        self.calls.append((payload, created_by))
        for a in self.actions:
            if a["status"] == "open" and (a["launch_id"], a["action_type"]) == (payload["launch_id"], payload["action_type"]):
                return a, False
        a = {**payload, "action_id": len(self.actions) + 1, "status": "open", "created_by": created_by,
             "due_date": str(payload["due_date"]), "created_at": "2026-09-22T09:00:00Z"}
        self.actions.append(a)
        return a, True


class FakeGenie:
    def __init__(self, result):
        self.result, self.calls = result, []

    def ask(self, question, space, conversation_id=None, user_token=None):
        self.calls.append((question, space, conversation_id, user_token))
        return self.result


@pytest.fixture
def repo():
    return FakeRepo()


def client(repo, genie=None):
    return TestClient(create_app(repo=repo, genie=genie or FakeGenie({"status": "ok", "text": "hi"})))


GOOD = {"launch_id": "ZYV-001", "action_type": "escalate_artwork", "owner": "Regulatory Artwork Manager",
        "due_date": "2026-09-29"}


def test_list_launches_sorted(repo):
    r = client(repo).get("/api/launches")
    assert r.status_code == 200 and [x["launch_id"] for x in r.json()] == ["ZYV-001", "ORB-001"]


def test_equipment_risk_limit(repo):
    assert len(client(repo).get("/api/equipment-risk?limit=1").json()) == 1


@pytest.mark.parametrize("bad", [{**GOOD, "action_type": "delete_everything"}, {**GOOD, "owner": ""},
                                 {k: v for k, v in GOOD.items() if k != "owner"}, {**GOOD, "due_date": "soon"}])
def test_post_action_validation_422(repo, bad):
    assert client(repo).post("/api/actions", json=bad).status_code == 422
    assert repo.calls == []


def test_post_action_is_idempotent_for_open_action(repo):
    c = client(repo)
    first = c.post("/api/actions", json=GOOD)
    second = c.post("/api/actions", json=GOOD)
    assert first.status_code == 201 and second.status_code == 200
    assert first.json()["action_id"] == second.json()["action_id"]
    assert len(c.get("/api/actions?launch_id=ZYV-001").json()) == 1


def test_created_by_comes_from_forwarded_user(repo):
    client(repo).post("/api/actions", json=GOOD, headers={"x-forwarded-email": "planner@helivara.example"})
    assert repo.calls[0][1] == "planner@helivara.example"
    assert repo.calls[0][0]["due_date"] == date(2026, 9, 29)


def test_utf8_note_roundtrip(repo):
    note = "Perché è urgente: qualità dell'artwork"
    r = client(repo).post("/api/actions", json={**GOOD, "note": note})
    assert r.json()["note"] == note and repo.calls[0][0]["note"] == note


def test_genie_ask_passes_user_token_and_space(repo):
    g = FakeGenie({"status": "ok", "text": "Zyvanta", "sql": "SELECT 1", "conversation_id": "c1"})
    r = client(repo, g).post("/api/genie/ask", json={"question": "Perché Zyvanta è a rischio?", "space": "demand"},
                             headers={"x-forwarded-access-token": "user-tok"})
    assert r.status_code == 200 and r.json()["text"] == "Zyvanta"
    assert g.calls[0] == ("Perché Zyvanta è a rischio?", "demand", None, "user-tok")


def test_genie_unknown_space_422(repo):
    assert client(repo).post("/api/genie/ask", json={"question": "x", "space": "hr"}).status_code == 422
