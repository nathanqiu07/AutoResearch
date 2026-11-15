"""Score decoys arms on the same proxy as petri_taste (see ../petri_taste/score.py), into this directory.

    python3 experiments/taste_petri/decoys/score.py run DC DZ --samples 3
    python3 experiments/taste_petri/decoys/score.py compare
"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "petri_taste"))
import score as S

S.RP.HERE = S.HERE = HERE
S.RP.CALLS_LOG = HERE / "calls.log"
S.RP.READ_CACHES = [HERE.parent / "petri_taste" / "cache", HERE.parent / "proxy" / "cache", HERE.parent / "arms" / "cache"]
S.ARMS = ("R0", "DC", "DZ")
S.PAIRS = [("DC", "R0"), ("DZ", "R0"), ("DC", "DZ")]

if __name__ == "__main__":
    if sys.argv[1] == "run":
        k = int(sys.argv[sys.argv.index("--samples") + 1])
        for arm in [a for a in sys.argv[2:] if not a.startswith("--") and not a.isdigit()]:
            S.RP.run(arm, k)
    else:
        print(S.compare("k3"))
