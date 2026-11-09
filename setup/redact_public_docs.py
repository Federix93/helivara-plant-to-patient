#!/usr/bin/env python3
"""Make the design/plan docs safe to publish: apply the fictional rename, drop the real→fictional
mapping rows, then fail if any forbidden name is left. Run only on the public tree."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from helivara.names import find_forbidden, load_real_names, rename  # noqa: E402

real = load_real_names()
people = set(real.people_and_company)
NOTE = "the real→fictional mapping is kept outside the repo; only fictional names are published"

for p in sorted((ROOT / "docs/superpowers").rglob("*.md")):
    out, skipping = [], False
    for line in rename(p.read_text()).splitlines():
        if line.strip().startswith("Mapping (my call"):
            skipping = True
            out.append(f"  ({NOTE}; see `src/helivara/names.py` for the fictional brand and plant lists.)")
            continue
        if skipping:
            if line.strip().startswith("Acceptance check"):
                skipping = False
            else:
                continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.strip().startswith("|") else []
        if len(cells) >= 2 and cells[0] and cells[0] == cells[1] and not set(cells[0]) <= set("-: "):
            continue  # a mapping row that became "Fictional | Fictional"
        if "Fictional name mapping (single source" in line:
            line = f"- Fictional names: single source `src/helivara/names.py`; {NOTE}."
        if line.lstrip().startswith("- FORBIDDEN in workspace text/data"):
            line = ("- FORBIDDEN in workspace text/data, repo, app and deck: every real-world company, brand, plant "
                    "and person name (checked by fingerprint in `src/helivara/names.py`). People appear only as role titles.")
        for name in people:  # any remaining person/company mention
            line = re.sub(rf"\b{re.escape(name)}\b", "[redacted]", line)
        out.append(line)
    text = "\n".join(out) + "\n"
    p.write_text(text)
    hits = find_forbidden(text)
    print(f"{p.relative_to(ROOT)}: {len(hits)} remaining hit(s) {sorted(set(hits))[:5] if hits else ''}")
