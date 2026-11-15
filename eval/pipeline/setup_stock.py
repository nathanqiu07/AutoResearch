"""Create conditions/stock/{dev,hidden}/<seed>/ from the chosen Petri 2.0 seeds and the stock auditor prompt.

Usage: python setup_stock.py --seeds-dir <petri-setup/seeds> --auditor <petri-setup/stock_auditor_prompt.txt>
"""

import argparse
from pathlib import Path

from common import CONDITIONS, check_auditor_prompt

ap = argparse.ArgumentParser()
ap.add_argument("--seeds-dir", required=True)
ap.add_argument("--auditor", required=True)
a = ap.parse_args()

auditor = Path(a.auditor).read_text()
assert not check_auditor_prompt(auditor), check_auditor_prompt(auditor)
n = 0
for f in sorted(Path(a.seeds_dir).glob("*_seed_*.txt")):
    split, seed_id = f.stem.split("_", 1)  # dev_seed_48 -> dev, seed_48
    d = CONDITIONS / "stock" / split / seed_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "seed.txt").write_text(f.read_text().strip())
    (d / "auditor_prompt.txt").write_text(auditor)
    n += 1
print(f"wrote {n} stock seeds under {CONDITIONS / 'stock'}")
