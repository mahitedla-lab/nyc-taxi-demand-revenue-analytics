#!/usr/bin/env python3
"""After `dbt build` on the synthetic sample, prove each data-quality rule caught exactly
the bad rows planted by ci/make_sample_data.py."""
import json
import sys
from pathlib import Path

import duckdb

HERE = Path(__file__).resolve().parent
con = duckdb.connect(str(HERE / "sample.duckdb"), read_only=True)
expected = json.loads((HERE / "expected_dq_counts.json").read_text())

actual = dict(con.execute("select rule_code, rows_failing_rule from staging.dq_exclusion_summary").fetchall())
raw_rows, valid_rows = con.execute("select max(total_rows), max(valid_rows) from staging.dq_exclusion_summary").fetchone()
fct_rows = con.execute("select count(*) from marts.fct_trips").fetchone()[0]

failures = []
print(f"{'rule':<6}{'expected':>10}{'actual':>10}")
for code in sorted(k for k in expected if k.startswith("DQ")):
    got = int(actual.get(code, 0))
    flag = "" if got == expected[code] else "   <-- MISMATCH"
    print(f"{code:<6}{expected[code]:>10}{got:>10}{flag}")
    if got != expected[code]:
        failures.append(code)

for label, want, got in [
    ("raw rows", expected["_raw_rows"], int(raw_rows)),
    ("valid rows", expected["_valid_rows"], int(valid_rows)),
    ("fct_trips rows", expected["_valid_rows"], int(fct_rows)),
]:
    print(f"{label:<16}{want:>10}{got:>10}{'' if want == got else '   <-- MISMATCH'}")
    if want != got:
        failures.append(label)

if failures:
    print("\nFAILED:", ", ".join(failures))
    sys.exit(1)
print("\nAll data-quality rules caught exactly the planted bad rows.")
