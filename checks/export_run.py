#!/usr/bin/env python3
"""Export every task of a job run as HTML (with outputs) plus a plain-text extract of the cell outputs,
so the execution evidence is readable as text. Usage: export_run.py <job_run_id> <out_dir>"""
import base64
import json
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from helivara.dbx import PROFILE  # noqa: E402

NOISE = re.compile(r"(UserWarning|warnings\.warn|protected_namespaces|threadpoolctl|match_module_callback|"
                   r"^\s+File \"|^\s+\^+|self\.\w+ = |config = get_config|module = module_class|"
                   r"AttributeError: 'NoneType' object has no attribute 'split'|Exception ignored|Traceback)")


def cli(*args):
    return json.loads(subprocess.run(["databricks", *args, "--profile", PROFILE, "-o", "json"],
                                     capture_output=True, text=True, check=True).stdout)


def to_text(data) -> str:
    if isinstance(data, list):
        return "".join(to_text(x) for x in data)
    if isinstance(data, dict):
        return to_text(data.get("data", "")) if "data" in data else json.dumps(data)
    return str(data or "")


def main(run_id: str, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    for t in cli("jobs", "get-run", run_id)["tasks"]:
        if "notebook_task" not in t:
            continue  # pipeline / SQL / python-file tasks have no notebook export (see run_summary.md, task logs)
        html = cli("jobs", "export-run", str(t["run_id"]), "--views-to-export", "CODE")["views"][0]["content"]
        (out / f"{t['task_key']}_run.html").write_text(html)
        m = re.search(r"__DATABRICKS_NOTEBOOK_MODEL = '([^']+)'", html)
        nb = json.loads(urllib.parse.unquote(base64.b64decode(m.group(1)).decode())) if m else {}
        lines = [f"# Job run {run_id} · task {t['task_key']} · state {t['state'].get('result_state')}",
                 f"# notebook: {nb.get('name', '')}", ""]
        for cmd in nb.get("commands", []):
            txt = re.sub("<[^>]+>", "", to_text((cmd.get("results") or {}).get("data")))
            txt = "\n".join(line for line in txt.splitlines() if line.strip() and not NOISE.search(line))
            if txt:
                lines += [f"--- cell {int(cmd.get('position', 0))} output ---", txt, ""]
        (out / f"{t['task_key']}_run_output.txt").write_text("\n".join(lines))
        print(t["task_key"], "->", out / f"{t['task_key']}_run_output.txt")


if __name__ == "__main__":
    main(sys.argv[1], Path(sys.argv[2]))
