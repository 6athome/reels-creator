"""Inspect local media without modifying the inputs."""
import argparse
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
IMAGES = {".jpg", ".jpeg", ".png", ".webp"}
VIDEOS = {".mp4", ".mov"}


def tool(name):
    found = shutil.which(name)
    if found:
        return found
    suffix = ".exe" if os.name == "nt" else ""
    local = ROOT / ".local-tools" / "ffmpeg" / (name + suffix)
    if local.is_file():
        return str(local)
    modules = ROOT / "remotion" / "node_modules"
    candidates = [*modules.glob(f"@remotion/compositor-*/{name}{suffix}"),
                  *modules.glob(f".pnpm/@remotion+compositor-*/node_modules/@remotion/compositor-*/{name}{suffix}")]
    for candidate in candidates:
        if candidate.is_file() and (os.name != "nt" or "win32" in str(candidate)):
            return str(candidate)
    raise RuntimeError(f"{name} 실행 파일을 찾을 수 없습니다. PATH 또는 Remotion 의존성을 확인하세요.")


def run(args, timeout=None):
    result = subprocess.run(list(map(str, args)), capture_output=True, encoding="utf-8",
                            errors="replace", timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}")
    return result.stdout


def probe(path, ffprobe):
    return json.loads(run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", "-protocol_whitelist", "file", path], timeout=45))


def positive(value):
    try:
        number = float(Fraction(str(value)))
        return number if math.isfinite(number) and number > 0 else None
    except (ValueError, ZeroDivisionError, OverflowError):
        return None


def inspect(path, relative, ffprobe, ffmpeg):
    kind = "image" if path.suffix.lower() in IMAGES else "video"
    entry = {"id": "m-" + hashlib.sha256(relative.encode("utf-8")).hexdigest()[:16],
             "filename": path.name, "relativePath": relative, "path": str(path),
             "kind": kind, "extension": path.suffix.lower().lstrip("."),
             "format": None, "codec": None, "width": None, "height": None, "duration": None, "fps": None,
             "hasAudio": None, "orientation": None, "rotation": None, "error": None}
    try:
        data = probe(path, ffprobe)
        streams = data.get("streams", [])
        stream = next((s for s in streams if s["codec_type"] == "video" and not
                       s.get("disposition", {}).get("attached_pic")), None)
        if not stream:
            raise ValueError("영상 또는 이미지 스트림을 찾을 수 없습니다.")
        width, height = int(stream["width"]), int(stream["height"])
        if kind == "image" and path.suffix.lower() == ".webp" and (width <= 0 or height <= 0):
            decoded = subprocess.run([ffmpeg, "-nostdin", "-v", "error", "-protocol_whitelist", "file", "-i", str(path),
                                      "-frames:v", "1", "-c:v", "png", "-f", "image2pipe", "-"],
                                     capture_output=True, timeout=60, check=False)
            if decoded.returncode or decoded.stdout[:8] != b"\x89PNG\r\n\x1a\n":
                raise ValueError(decoded.stderr.decode("utf-8", errors="replace").strip() or "WebP를 디코딩할 수 없습니다.")
            width, height = struct.unpack(">II", decoded.stdout[16:24])
        if width <= 0 or height <= 0:
            raise ValueError("잘못된 해상도입니다.")
        rotation = next((s["rotation"] for s in stream.get("side_data_list", []) if "rotation" in s),
                        stream.get("tags", {}).get("rotate", 0))
        rotation = round(float(rotation)) % 360
        if rotation in (90, 270):
            width, height = height, width
        duration = positive(stream.get("duration")) or positive(data.get("format", {}).get("duration"))
        fps = positive(stream.get("avg_frame_rate")) or positive(stream.get("r_frame_rate"))
        entry.update(format=data.get("format", {}).get("format_name"), codec=stream.get("codec_name"),
                     width=width, height=height,
                     duration=duration if kind == "video" else None, fps=fps if kind == "video" else None,
                     hasAudio=kind == "video" and any(s["codec_type"] == "audio" for s in streams),
                     orientation="landscape" if width > height else "portrait" if height > width else "square",
                     rotation=rotation)
        if kind == "video" and duration is None:
            raise ValueError("영상 길이를 확인할 수 없습니다.")
        run([ffmpeg, "-nostdin", "-v", "error", "-xerror", "-protocol_whitelist", "file", "-i", path, "-map", f"0:{stream['index']}",
             "-frames:v", "1", "-c:v", "png", "-f", "null", "-"], timeout=60)
    except (RuntimeError, ValueError, OSError, KeyError, subprocess.TimeoutExpired) as error:
        entry["error"] = str(error)
    return entry


def scan(folder):
    root = Path(folder).resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"입력 폴더가 아닙니다: {root}")
    ffprobe, ffmpeg = tool("ffprobe"), tool("ffmpeg")
    paths = sorted((p for p in root.rglob("*") if p.is_file() and not p.is_symlink()
                    and p.suffix.lower() in IMAGES | VIDEOS),
                   key=lambda p: (p.relative_to(root).as_posix().casefold(), p.as_posix()))
    assets = []
    for path in paths:
        resolved = path.resolve(strict=True)
        if resolved.is_relative_to(root):
            assets.append(inspect(resolved, path.relative_to(root).as_posix(), ffprobe, ffmpeg))
    return {"schemaVersion": 1, "inputRoot": str(root), "analysisMode": "metadata-and-first-frame-decode",
            "mediaAssets": assets}


def write_json(path, data):
    with Path(path).open("x", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2, allow_nan=False)
        file.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        write_json(args.output, scan(args.folder))
        print(args.output.resolve())
    except (OSError, ValueError, RuntimeError) as error:
        sys.exit(f"[scan] {error}")
