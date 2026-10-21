"""Download the LaDe authors' code at the pinned commit and make it runnable (it has no license, so it is not copied
into this repository).

    uv run python -m evidence.leaks.setup

Steps: shallow-fetch github.com/wenhaomin/LaDe @ COMMIT into evidence/leaks/LaDe/; apply fixes.diff (the 7 fixes
their code needs to run at all); copy the GAT encoder their M2G4RTP delivery model imports but does not ship; add a
geohash encoder in place of the geohash2 package (its wheel does not build); link our Yantai CSV where their code
expects it.

Then:
    uv run python -m evidence.leaks.check                          # prove the leaks (no extra dependencies)
    # to rerun their models: a separate Python env with PyTorch + LaDe/time_prediction/requirements.txt, then
    python evidence/leaks/LaDe/time_prediction/data/dataset_delivery.py
    python evidence/leaks/train.py delivery_yt m2g4rtp_delivery    # their model, their scoring
    python evidence/leaks/rescore.py delivery_yt <checkpoint>      # same model, scored per package
    python evidence/leaks/clean.py                                 # leak-free copies of their data pipeline
"""

import shutil
import subprocess
from pathlib import Path

from server.config import RAW_DIR

REPO = "https://github.com/wenhaomin/LaDe.git"
COMMIT = "9e5155a5e03b0e752749f726914f73bf08d62666"
HERE = Path(__file__).resolve().parent
LADE = HERE / "LaDe"
TP = LADE / "time_prediction"

GEOHASH = '''"""Standard geohash encoder (stand-in for the geohash2 package)."""
_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


def encode(latitude, longitude, precision=12):
    lat, lng, bits, bit, chars, even = [-90.0, 90.0], [-180.0, 180.0], 0, 0, [], True
    while len(chars) < precision:
        span, value = (lng, longitude) if even else (lat, latitude)
        mid = (span[0] + span[1]) / 2
        bits = bits * 2 + (value > mid)
        span[value <= mid] = mid
        even, bit = not even, bit + 1
        if bit == 5:
            chars.append(_BASE32[bits])
            bits, bit = 0, 0
    return "".join(chars)
'''


def git(*args: str) -> None:
    subprocess.run(["git", "-C", str(LADE), *args], check=True)


def main() -> None:
    if not LADE.exists():
        LADE.mkdir(parents=True)
        git("init", "-q")
        git("remote", "add", "origin", REPO)
        git("fetch", "-q", "--depth", "1", "origin", COMMIT)
        git("checkout", "-q", "FETCH_HEAD")
        git("apply", str(HERE / "fixes.diff"))
        shutil.copy(LADE / "route_prediction/algorithm/m2g4rtp_pickup/gat_encoder.py", TP / "algorithm/m2g4rtp_delivery/gat_encoder.py")
        (TP / "geohash2.py").write_text(GEOHASH, encoding="utf-8")
    source, target = RAW_DIR / "delivery_yt.csv", TP / "data/raw_data/delivery/delivery_yt.csv"
    if source.exists() and not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source, target)
    print(f"LaDe @ {COMMIT[:7]} ready in {LADE}")


if __name__ == "__main__":
    main()
