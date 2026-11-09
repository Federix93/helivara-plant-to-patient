"""Genie Conversation API client. Never raises to the caller: every outcome is a dict with
status ok | no_data | error, so the UI can always render something."""
from __future__ import annotations

import os
import time
from typing import Callable


def _default_http(method: str, path: str, body=None, token=None) -> dict:
    import httpx
    from databricks.sdk.core import Config

    cfg = Config()
    headers = {"Authorization": f"Bearer {token}"} if token else cfg.authenticate()
    r = httpx.request(method, f"{cfg.host.rstrip('/')}{path}", json=body, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json() if r.content else {}


class GenieClient:
    def __init__(self, spaces: dict[str, str], http: Callable = _default_http, sleep: Callable = time.sleep,
                 clock: Callable = time.monotonic, timeout_s: float = 60, poll_s: float = 2):
        self.spaces, self.http, self.sleep, self.clock = spaces, http, sleep, clock
        self.timeout_s, self.poll_s = timeout_s, poll_s

    @classmethod
    def from_env(cls) -> "GenieClient":
        return cls({"demand": os.environ["GENIE_DEMAND_SPACE_ID"],
                    "manufacturing": os.environ["GENIE_MFG_SPACE_ID"]})

    def ask(self, question: str, space: str, conversation_id: str | None = None, user_token: str | None = None) -> dict:
        sid = self.spaces[space]
        base = f"/api/2.0/genie/spaces/{sid}"
        out = {"conversation_id": conversation_id, "status": "error", "text": "", "sql": None, "columns": None, "rows": None}
        try:
            if conversation_id:
                m = self.http("POST", f"{base}/conversations/{conversation_id}/messages", {"content": question}, user_token)
                mid = m.get("message_id") or m.get("id")
            else:
                m = self.http("POST", f"{base}/start-conversation", {"content": question}, user_token)
                conversation_id, mid = m["conversation_id"], m["message_id"]
            out["conversation_id"] = conversation_id
            t0 = self.clock()
            while True:
                msg = self.http("GET", f"{base}/conversations/{conversation_id}/messages/{mid}", None, user_token)
                status = msg.get("status")
                if status in ("COMPLETED", "FAILED", "CANCELLED"):
                    break
                if self.clock() - t0 >= self.timeout_s:
                    out["text"] = "Genie is taking longer than usual. Please try again in a moment."
                    return out
                self.sleep(self.poll_s)
            if status != "COMPLETED":
                err = msg.get("error") or {}
                out["text"] = f"Genie could not answer: {err.get('error') or err.get('message') or status}"
                return out
            texts = []
            for a in msg.get("attachments") or []:
                if "text" in a:
                    texts.append(a["text"].get("content", ""))
                if "query" in a:
                    q = a["query"]
                    out["sql"] = q.get("query")
                    if q.get("description"):
                        texts.append(q["description"])
                    r = self.http("GET", f"{base}/conversations/{conversation_id}/messages/{mid}"
                                         f"/attachments/{a['attachment_id']}/query-result", None, user_token) or {}
                    sr = r.get("statement_response", {})
                    out["columns"] = [c["name"] for c in sr.get("manifest", {}).get("schema", {}).get("columns", [])]
                    out["rows"] = (sr.get("result", {}).get("data_array") or [])[:50]
            out["text"] = "\n\n".join(t for t in texts if t)
            out["status"] = "no_data" if out["sql"] and not out["rows"] else "ok"
            return out
        except Exception as e:  # network/auth errors become a renderable message
            out["text"] = f"Genie is unavailable right now ({type(e).__name__})."
            return out
