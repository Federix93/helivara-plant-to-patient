#!/usr/bin/env python3
"""Generate the raw source extracts and land them in the UC Volume `raw` (simulated SAP/MES/IoT/CMMS)."""
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from helivara.dbx import CATALOG, PROFILE, SCHEMA, sql  # noqa: E402
from helivara.generate import build_tables, write_raw  # noqa: E402

OUT = Path("raw_out")
VOL = f"dbfs:/Volumes/{CATALOG}/{SCHEMA}/raw"

if __name__ == "__main__":
    sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.raw COMMENT "
        f"'Landing zone for simulated source extracts (SAP, MES, IoT, CMMS) - synthetic data'")
    shutil.rmtree(OUT, ignore_errors=True)
    tables = build_tables()
    for name, p in write_raw(tables, OUT).items():
        print(f"{name:28s} {len(tables[name]):7d} rows -> {p}")
    for sub in ["sap", "mes", "iot", "cmms", "config"]:
        subprocess.run(["databricks", "fs", "rm", "-r", f"{VOL}/{sub}", "--profile", PROFILE],
                       capture_output=True)
    subprocess.run(["databricks", "fs", "cp", "-r", str(OUT), VOL, "--overwrite", "--profile", PROFILE],
                   check=True)
    shutil.copy(OUT / "_dirty_manifest.json", Path("evidence/pipeline/dirty_manifest.json"))
    print("landed in", VOL)
