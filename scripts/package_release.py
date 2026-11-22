"""Build a release and ZIP from the reviewed source and synthetic demos."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from doctor import checked_files  # noqa: E402

SAMPLES = {
    Path("remotion/public/demo/test-backdrop.jpg"): (0, b"\xff\xd8\xff"),
    Path("examples/demo-cover.png"): (0, b"\x89PNG\r\n\x1a\n"),
    Path("examples/demo-reel.mp4"): (4, b"ftyp"),
}
RESTRICTED = re.compile(
    r"(?:[A-Z]:\\{1,2}(?:Users|Documents and Settings)\\|/(?:Users|home)/[a-z][\w.-]+/|"
    r"github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{25,}|"
    r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)",
    re.IGNORECASE,
)


def audit(paths):
    for relative in paths:
        path = ROOT / relative
        if path.stat().st_size > 1_000_000:
            raise ValueError(f"Large release file: {relative}")
        if relative in SAMPLES:
            offset, magic = SAMPLES[relative]
            if path.read_bytes()[offset:offset + len(magic)] != magic:
                raise ValueError(f"Unexpected data in sample: {path}")
            continue
        data = path.read_text(encoding="utf-8")
        if RESTRICTED.search(data):
            raise ValueError(f"Possible private path or credential: {relative}")
    if json.loads((ROOT / "config/local-fonts.json").read_text(encoding="utf-8")) != {"fonts": []}:
        raise ValueError("Public font configuration must be empty.")
    lock = json.loads((ROOT / "remotion/package-lock.json").read_text(encoding="utf-8"))
    for name, dependency in lock["packages"].items():
        if name and (not dependency.get("resolved", "").startswith("https://registry.npmjs.org/") or
                     not dependency.get("integrity", "").startswith("sha512-")):
            raise ValueError(f"Unapproved lockfile source: {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    paths = list(checked_files())
    audit(paths)
    base = args.destination.resolve()
    base.mkdir(parents=True)
    release = base / "reels-creator"
    for relative in paths:
        target = release / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    archive = base / "reels-creator.zip"
    with ZipFile(archive, "x", ZIP_DEFLATED, compresslevel=9) as out:
        for relative in paths:
            out.write(release / relative, (Path(release.name) / relative).as_posix())
    print(f"{len(paths)} files | {archive.stat().st_size} bytes", flush=True)
    print(f"SHA-256 {hashlib.sha256(archive.read_bytes()).hexdigest()}", flush=True)
    print(archive)


if __name__ == "__main__":
    main()
