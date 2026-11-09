"""Fictional names for Helivara and a scanner that keeps real-world names out.

Helivara is a fictional company. This module only ever contains fictional names. Real-world
names that must never appear are stored as SHA-256 fingerprints (lower-cased), so the scanner
works without publishing them. The real→fictional rename map is only used locally to migrate
legacy material; it lives in the git-ignored file legacy/real_names.json.

CLI: `python -m helivara.names <files...>` prints hits and exits 1 if any are found.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

FICTIONAL_BRANDS = ["Zyvanta", "Oribex", "Gastrelle", "Colvera", "Florabis", "Lactavio",
                    "Refluxa", "Venoria", "Faringel", "Digestin", "Citralux"]
FICTIONAL_PLANTS = ["Valmora", "Castelverde", "Roccalba", "Riberal", "Ashbury Ridge"]
HERO_LAUNCH_ID = "ZYV-001"
PHASE_OUT_LAUNCH_ID = "ORB-001"

FORBIDDEN_SHA256 = frozenset({
    "06836d4b6b12155abedad60c00df39882be8025c333e51edde5c850020e30958",
    "9662044e914819308e355349f469e0945bcfe4ab6c1b13bb5dfe6e89f134173e",
    "fe6755d9bb568a9e09274f0300e04732fdb07b763ea2e42bd203c1a0655415f5",
    "9b358b557bc35e15812a10aec03f1ce004e8c522f5812a106a9d349e9a742ba3",
    "c4002f1cdaf6cc5dddbe132e38248cfedd1176d65f2e93268f28ee0269899975",
    "2aeaa3711cd9851afc795ffab0a981d03641642b8a28ae1502f7eb41fc0ef7ed",
    "ceea29409bdc5125dbce5893163e9e75641718544d98df7d66f22b600dec9b60",
    "2df5712e1cf303a50fac51e4b2c0ac71884f746b20f206f9df2eb6375fde7270",
    "499de9baa20fac459cf41e41881668cf36d0989abfc5e9adeef55736867d88ca",
    "5d32a7967d0dff64680d796939325767af9a8606d0431822fa0f328f1a07c995",
    "0f07b601d88c88ec79eeac16bd05cbbd014b99ae45df1fcb0f80a221418e81c0",
    "27f78109d2a57f35838bcc2e093130932ec64c959964a16692813c5697ce27b4",
    "f56136184bf0e5b38f5ae007d629870c749d68d499dd50bc8755046692f3f8dd",
    "e88a07e88d9ebcf5708d3f7371dbff1dde743054b0115ce3214d1903284a7b58",
    "e81381725666468f4c8cdeb3c77d7dd0746930d7dc29081b43a24f1d2cb564dc",
    "dafcc41694bf06971fbd2fd48bbba5d6d710853e4564c1defe5bd61a2488650f",
    "29112fa26dbb637261a622ce989663ce5f2446d68581d2af15420df0d596ad2d",
    "a1cc94c5233235c4698fc078c3d4bd9e14937337520c956a82a07ec059ecfcab",
    "af7f04cff61fc48b570f1e1f5dd0dd0d080cc32b2179f3468b337cb85a338e78",
    "dcaf6926f58263d6dc98cd67136967882ebbcec0caabc8d1171ccddcc45e9c8d",
    "ca0b642ed0c1c9902c3e9c8ac00865e0a9cf6449f66012e1c6948b66818f26ff",
    "7ae53d2daa5b2cd25f8590eda0e590732e805e268c82cdf5dee4664ba6525d1d"
})

REAL_NAMES_FILE = Path(__file__).resolve().parents[2] / "legacy" / "real_names.json"
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*")


def _fp(word: str) -> str:
    return hashlib.sha256(word.lower().encode("utf-8")).hexdigest()


def find_forbidden(text: str) -> list[str]:
    """Return tokens of `text` that are forbidden real names (as written, in order)."""
    hits = []
    for m in _TOKEN_RE.finditer(text or ""):
        tok = m.group(0)
        parts = [tok] + (tok.split("-") if "-" in tok else [])
        if any(_fp(p) in FORBIDDEN_SHA256 for p in parts):
            hits.append(tok)
    return hits


@dataclass(frozen=True)
class RealNames:
    brand_map: dict
    plant_map: dict
    supplier_map: dict
    launch_id_map: dict
    people_and_company: list

    @property
    def forbidden(self) -> list[str]:
        return (list(self.brand_map) + list(self.plant_map) + list(self.supplier_map)
                + list(self.people_and_company))

    @property
    def all_maps(self) -> dict:
        return {**self.brand_map, **self.plant_map, **self.supplier_map, **self.launch_id_map}


def load_real_names(missing_ok: bool = False) -> RealNames | None:
    if not REAL_NAMES_FILE.exists():
        if missing_ok:
            return None
        raise FileNotFoundError(f"{REAL_NAMES_FILE} is required to rename legacy material")
    return RealNames(**json.loads(REAL_NAMES_FILE.read_text(encoding="utf-8")))


def rename(text: str) -> str:
    """Replace real names with fictional ones (whole words, longest first). Local use only."""
    maps = load_real_names().all_maps
    rx = re.compile("|".join(rf"(?<![\w-]){re.escape(k)}(?![\w-])"
                             for k in sorted(maps, key=len, reverse=True)))
    return rx.sub(lambda m: maps[m.group(0)], text)


def _main(paths: list[str]) -> int:
    hits = 0
    for p in paths:
        path = Path(p)
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        found = find_forbidden(text)
        if found:
            hits += len(found)
            print(f"{p}: {len(found)} hit(s)")
    print(f"forbidden-name hits: {hits}")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
