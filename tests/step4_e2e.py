"""Run local end-to-end cases with generated, non-user media."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from media_scanner import run, tool, write_json  # noqa: E402

ENGINE = ROOT / "scripts/reel_engine.py"


def call(*args, expected=None):
    command = [sys.executable, str(ENGINE), *map(str, args)]
    if expected is None:
        subprocess.run(command, check=True)
    else:
        result = subprocess.run(command, capture_output=True, encoding="utf-8", errors="replace")
        assert result.returncode and expected in result.stderr, result.stderr
        print(f"[expected error] {result.stderr.strip()}", flush=True)


def make_inputs(base):
    photos, movies, mixed = (base / name for name in ("사진 5장", "영상 3개", "혼합 [촬영]&원본"))
    for folder in (photos, movies, mixed):
        folder.mkdir(parents=True)
    ffmpeg = os.environ.get("REELS_TEST_FFMPEG") or tool("ffmpeg")
    colors = ("0x674565", "0x4E746D", "0x8A4B47", "0x455D7A", "0x9C6A38")
    for i, (extension, color) in enumerate(zip(("jpg", "jpeg", "png", "webp", "png"), colors), 1):
        path = photos / f"{i:02d} 사진 & {i}.{extension}"
        run([ffmpeg, "-v", "error", "-f", "lavfi", "-i", f"color=c={color}:s=360x640",
             "-vf", f"drawbox=x={i*27}:y=185:w=125:h=220:color=0xE8C4A0:t=fill", "-frames:v", 1, path])
    for i, (size, extension) in enumerate((("640x360", "mp4"), ("360x640", "mov"), ("640x360", "mp4")), 1):
        path = movies / f"{i:02d} 장면 [{i}].{extension}"
        # The first and third clips have tones at different frequencies; the second is silent.
        command = [ffmpeg, "-v", "error", "-f", "lavfi", "-i",
                   f"testsrc2=size={size}:rate=15:duration=11"]
        if i != 2:
            command += ["-f", "lavfi", "-i", f"sine=frequency={330*i}:sample_rate=48000:duration=11", "-c:a", "aac"]
        command += ["-vf", f"drawbox=x=20:y=20:w=90:h=72:color={colors[i-1]}:t=fill",
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", path]
        run(command)
    import shutil
    shutil.copyfile(next(photos.glob("*.webp")), mixed / "01 시작.webp")
    shutil.copyfile(sorted(movies.glob("*.mp4"))[0], mixed / "02 전경 [가로].mp4")
    shutil.copyfile(next(photos.glob("*.jpeg")), mixed / "03 마지막.jpeg")
    (mixed / "04 손상.png").write_bytes(b"not a valid image")
    music = base / "직접 생성한 음악.wav"
    run([ffmpeg, "-v", "error", "-f", "lavfi", "-i", "sine=frequency=660:sample_rate=48000:duration=2", music])
    return photos, movies, mixed, music


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check(out, name, version, seconds, audio):
    root = out / name / version
    report = load(root / "render-report.json")
    assert report["status"] == "success" and report["hasAudio"] == audio, report
    assert report["frames"] == seconds * 30 and report["videoSeconds"] == seconds, report
    assert report["width"] == 1080 and report["height"] == 1920 and report["codec"] == "h264", report
    assert (root / "cover.png").stat().st_size > 24
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_root", type=Path)
    parser.add_argument("--resume-after-mixed", action="store_true")
    args = parser.parse_args()
    root = args.run_root.resolve()
    out = root / "results"
    if not args.resume_after_mixed:
        root.mkdir(parents=True)
        photos, movies, mixed, music = make_inputs(root / "inputs")
        call("auto", photos, "--project-id", "a-photos", "--title", "사진으로 남긴 하루", "--seconds", 15,
             "--cover", "storytelling", "--photo-motion", "pan-right", "--output", out)
        call("auto", movies, "--project-id", "b-videos", "--title", "세 장면의 기록", "--seconds", 30,
             "--cover", "bold-hook", "--fit", "contain", "--source-volume", ".7", "--output", out)
        call("plan", mixed, "--project-id", "c-mixed", "--title", "공간", "--hook", "이 공간의 첫인상은?",
             "--seconds", 9, "--cover", "playful-impact", "--music", music, "--mute-source", "--output", out)
        call("render", out / "c-mixed/v001/reel-project.json", "--output", out)
    a = check(out, "a-photos", "v001", 15, False)
    assert len(load(a / "reel-project.json")["clips"]) == 5
    b = check(out, "b-videos", "v001", 30, True)
    manifest = load(b / "media-manifest.json")
    assert any(x["orientation"] == "landscape" for x in manifest["mediaAssets"])
    assert any(x["kind"] == "video" and x["hasAudio"] is False for x in manifest["mediaAssets"])
    draft = out / "c-mixed/v001/reel-project.json"
    assert not (draft.parent / "reel.mp4").exists()
    assert any(x["error"] for x in load(draft.parent / "media-manifest.json")["mediaAssets"])
    c = check(out, "c-mixed", "v002", 9, True)
    call("plan", root / "missing", "--project-id", "missing", "--title", "누락", "--output", out, expected="[scan]")
    broken = load(c / "reel-project.json")
    broken["mediaAssets"][0]["path"] = str(root / "does not exist.jpg")
    invalid_path = root / "invalid-path.json"
    write_json(invalid_path, broken)
    call("validate", invalid_path, expected="[validate]")
    extended = load(b / "reel-project.json")
    extended["clips"][0].update(sourceEnd=12, durationFrames=360)
    invalid_range = root / "invalid-range.json"
    write_json(invalid_range, extended)
    call("validate", invalid_range, expected="원본 영상 길이")
    edited = load(c / "reel-project.json")
    edited["clips"].reverse()
    edited["clips"][0].update(sourceEnd=2, durationFrames=60)
    edited["clips"][1].update(sourceStart=2, sourceEnd=6, durationFrames=120)
    cursor = 0
    for cut in edited["clips"]:
        cut["timelineStartFrame"] = cursor
        cursor += cut["durationFrames"]
    edited["captions"][0]["text"] = "순서와 길이를 바꿨어요"
    edited["captions"][0]["style"] = {"fontSizePx": 52, "backgroundColor": "#003E2F"}
    edited["audioSettings"]["musicPath"] = None
    edit_path = root / "edited.json"
    write_json(edit_path, edited)
    call("render", edit_path, "--output", out)
    d = check(out, "c-mixed", "v003", 9, False)
    assert (c / "reel.mp4").read_bytes() != (d / "reel.mp4").read_bytes()
    print("[tests] A–I workflow assertions passed", flush=True)


if __name__ == "__main__":
    main()
