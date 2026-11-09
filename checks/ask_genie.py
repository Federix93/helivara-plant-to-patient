#!/usr/bin/env python3
"""Ask a Genie space a question via the Conversation API and record question, answer, SQL and rows.
Usage: ask_genie.py <space_id> "<question>" [--out evidence/genie/x.json]"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from helivara.dbx import api  # noqa: E402


def ask(space_id: str, question: str, conversation_id: str | None = None, timeout_s: int = 180) -> dict:
    if conversation_id:
        m = api("POST", f"/api/2.0/genie/spaces/{space_id}/conversations/{conversation_id}/messages", {"content": question})
        cid, mid = conversation_id, m["message_id"] if "message_id" in m else m["id"]
    else:
        m = api("POST", f"/api/2.0/genie/spaces/{space_id}/start-conversation", {"content": question})
        cid, mid = m["conversation_id"], m["message_id"]
    t0 = time.time()
    while True:
        msg = api("GET", f"/api/2.0/genie/spaces/{space_id}/conversations/{cid}/messages/{mid}")
        if msg.get("status") in ("COMPLETED", "FAILED", "CANCELLED") or time.time() - t0 > timeout_s:
            break
        time.sleep(3)
    out = {"space_id": space_id, "question": question, "conversation_id": cid, "status": msg.get("status"),
           "text": [], "sql": None, "columns": None, "rows": None}
    for a in msg.get("attachments") or []:
        if "text" in a:
            out["text"].append(a["text"].get("content", ""))
        if "query" in a:
            q = a["query"]
            out["sql"] = q.get("query")
            if q.get("description"):
                out["text"].append(q["description"])
            r = api("GET", f"/api/2.0/genie/spaces/{space_id}/conversations/{cid}/messages/{mid}"
                           f"/attachments/{a['attachment_id']}/query-result")
            sr = r.get("statement_response", {})
            out["columns"] = [c["name"] for c in sr.get("manifest", {}).get("schema", {}).get("columns", [])]
            out["rows"] = (sr.get("result", {}).get("data_array") or [])[:20]
    out["text"] = "\n".join(out["text"])
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("space_id")
    ap.add_argument("question")
    ap.add_argument("--out")
    a = ap.parse_args()
    res = ask(a.space_id, a.question)
    print(json.dumps(res, indent=1, ensure_ascii=False))
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(res, indent=1, ensure_ascii=False))
