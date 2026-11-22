"""Build a release and ZIP from the reviewed source and synthetic demos."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from doctor import checked_files  # noqa: E402

SAMPLES = {
    Path("remotion/public/demo/test-backdrop.jpg"): "43b0e6abd923fa500f3c3fa57fe3e262437db4a290830d2b4803fc568b11e1b7",
    Path("examples/demo-cover.png"): "8bba8a74a1c623a72cda86df6286b110c851c18b0a53a30ae2343cde5453df68",
    Path("examples/demo-reel.mp4"): "18dab79987fe3252f904c740e30103ba278c9d5625d41ca5fc3a6bb718e668ab",
}
PRIVATE_NAMES = {"media-manifest.json", "reel-project.json", "captions.json", "render-report.json", "caption-color-report.json"}
PRIVATE_DIRS = {"reels-workspace", "input", "projects", "output", "user-samples", "node_modules", "fonts"}
PUBLIC_SUFFIXES = {".py", ".cjs", ".ts", ".tsx", ".md", ".json", ".ps1", ".sh", ".txt", ".yaml"}
PUBLIC_NAMES = {".gitignore", "LICENSE", "VERSION"}
RESTRICTED = re.compile(
    r"(?:(?<![\w-])[A-Z]:[\\/]+(?=[\w.])|/(?:Users|home|Volumes|mnt)/[\w.-]+/|"
    r"github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{25,}|"
    r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)",
    re.IGNORECASE,
)


def audit(paths, read=lambda relative: (ROOT / relative).read_bytes()):
    for relative in paths:
        if relative.name.casefold() in PRIVATE_NAMES or any(part.casefold() in PRIVATE_DIRS for part in relative.parts):
            raise ValueError(f"Private directory in release: {relative}")
        data = read(relative)
        if len(data) > 1_000_000:
            raise ValueError(f"Large release file: {relative}")
        if relative in SAMPLES:
            if hashlib.sha256(data).hexdigest() != SAMPLES[relative]:
                raise ValueError(f"Synthetic demo was replaced: {relative}")
            continue
        if relative.suffix not in PUBLIC_SUFFIXES and relative.as_posix() not in PUBLIC_NAMES:
            raise ValueError(f"Unexpected release file type: {relative}")
        if RESTRICTED.search(data.decode("utf-8")):
            raise ValueError(f"Possible private path or credential: {relative}")
    if json.loads(read(Path("config/local-fonts.json"))) != {"fonts": []}:
        raise ValueError("Public font configuration must be empty.")
    lock = json.loads(read(Path("remotion/package-lock.json")))
    for name, dependency in lock["packages"].items():
        if name and (not dependency.get("resolved", "").startswith("https://registry.npmjs.org/") or
                     not dependency.get("integrity", "").startswith("sha512-")):
            raise ValueError(f"Unapproved lockfile source: {name}")


def git_bytes(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def audit_git_tree(commit=None):
    if commit is None:
        records = git_bytes("ls-files", "--stage", "-z")
    else:
        revision = git_bytes("rev-parse", "--verify", "--end-of-options", f"{commit}^{{commit}}").decode("ascii").strip()
        records = git_bytes("ls-tree", "-r", "-z", revision)
    entries = {}
    for record in filter(None, records.split(b"\0")):
        metadata, name = record.split(b"\t", 1)
        fields = metadata.decode("ascii").split()
        mode, oid, entry_type = (fields[0], fields[2], fields[1]) if commit is not None else fields
        if entry_type not in {"0", "blob"} or mode not in {"100644", "100755"}:
            raise ValueError(f"Unexpected Git entry: {name.decode('utf-8')}")
        entries[Path(name.decode("utf-8"))] = oid

    def read(relative):
        return git_bytes("cat-file", "blob", entries[relative])

    if Path("release-files.txt") not in entries:
        raise ValueError("Git tree is missing release-files.txt")
    allowed = {Path(name) for name in read(Path("release-files.txt")).decode("utf-8").splitlines()}
    if entries.keys() != allowed or not SAMPLES.keys() <= allowed:
        raise ValueError(f"Git tree differs from the release list. Extra: {entries.keys() - allowed}; missing: {allowed - entries.keys()}")
    audit(sorted(allowed), read)
    print(f"Git {'commit' if commit is not None else 'index'} verified: {len(allowed)} files")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, nargs="?")
    checks = parser.add_mutually_exclusive_group()
    checks.add_argument("--check-index", action="store_true", help="Audit exactly the bytes staged in Git")
    checks.add_argument("--check-commit", metavar="REF", help="Audit the tree of a commit before push")
    args = parser.parse_args()
    if args.check_index or args.check_commit:
        if args.destination:
            parser.error("choose a destination or a Git check")
        audit_git_tree(args.check_commit)
        return
    if not args.destination:
        parser.error("choose a destination or a Git check")
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
