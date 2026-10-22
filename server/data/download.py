"""Download an untouched LaDe-D city delivery CSV from the pinned Hugging Face revision, with checksum checks."""

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from server.config import CITIES, DATA_DIR, HF_REPO, HF_REVISION, RAW_DIR, RIGHTS, ROAD_CITY, ROOT


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(path: Path, entry: dict) -> str:
    """Check size and the Hugging Face LFS SHA-256 (or git blob SHA-1 for non-LFS files)."""
    if path.stat().st_size != entry["size"]:
        raise ValueError(f"Unexpected file size: {path}")
    digest = sha256_file(path)
    if "lfs" in entry:
        if digest != entry["lfs"]["oid"]:
            raise ValueError(f"SHA-256 mismatch: {path}")
    else:
        blob = hashlib.sha1(f"blob {path.stat().st_size}\0".encode())
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                blob.update(chunk)
        if blob.hexdigest() != entry["oid"]:
            raise ValueError(f"Git blob hash mismatch: {path}")
    return digest


def _csv_summary(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        columns = next(reader)
        return {"row_count": sum(1 for row in reader if row), "columns": columns}


def fetch(source_path: str) -> tuple[Path, dict, str, bool]:
    """Download a file from the pinned revision if missing and verify it. Returns path, listing entry, url, downloaded."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    output = RAW_DIR / Path(source_path).name
    url = f"https://huggingface.co/datasets/{HF_REPO}/resolve/{HF_REVISION}/{source_path}"
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    with requests.Session() as session:
        session.mount("https://", HTTPAdapter(max_retries=retry))
        folder = source_path.rsplit("/", 1)[0]
        listing = session.get(f"https://huggingface.co/api/datasets/{HF_REPO}/tree/{HF_REVISION}/{folder}", timeout=60)
        listing.raise_for_status()
        entry = next(item for item in listing.json() if item["path"] == source_path)
        downloaded = not output.exists()
        if downloaded:
            part = output.with_suffix(output.suffix + ".part")
            try:
                with session.get(url, stream=True, timeout=(30, 120)) as response:
                    response.raise_for_status()
                    with part.open("wb") as stream:
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            stream.write(chunk)
                verify(part, entry)
                part.replace(output)
            finally:
                part.unlink(missing_ok=True)
    verify(output, entry)
    return output, entry, url, downloaded


def download_roads() -> list[Path]:
    """Every city's OpenStreetMap roads from LaDe's road network file (data/raw/roads_<city>.csv)."""
    source, _, _, _ = fetch("road-network/roads.csv")
    roads = pd.read_csv(source, sep="	", usecols=["fclass", "city", "geometry"])
    outputs = []
    for city, name in ROAD_CITY.items():
        outputs.append(RAW_DIR / f"roads_{city}.csv")
        roads.loc[roads["city"] == name, ["fclass", "geometry"]].to_csv(outputs[-1], index=False)
    source.unlink()
    return outputs


def download_city(city: str) -> dict:
    """Download (if missing), verify, and write data/manifest_<city>.json. Returns the manifest."""
    source_path = f"delivery/delivery_{city}.csv"
    manifest_path = DATA_DIR / f"manifest_{city}.json"
    output, entry, url, downloaded = fetch(source_path)
    digest = verify(output, entry)
    previous = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    retrieved = datetime.now(timezone.utc).isoformat()
    if not downloaded and previous.get("sha256") == digest:
        retrieved = previous.get("retrieved_at_utc", retrieved)
    manifest = {
        "dataset": HF_REPO,
        "subdataset": "LaDe-D",
        "task": "delivery",
        "revision": HF_REVISION,
        "city": CITIES[city],
        "source_url": url,
        "selected_file": source_path,
        "local_file": output.relative_to(ROOT).as_posix(),
        "retrieved_at_utc": retrieved,
        "bytes": output.stat().st_size,
        "sha256": digest,
        **_csv_summary(output),
        "subset_rule": "One complete city delivery CSV; no sampling at download.",
        "modifications": "None; raw download preserved byte-for-byte.",
        "rights_statement": RIGHTS,
        "paper_url": "https://arxiv.org/html/2306.10675v3",
        "citation": "Wu et al., LaDe: The First Comprehensive Last-mile Delivery Dataset from Industry, arXiv:2306.10675.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
