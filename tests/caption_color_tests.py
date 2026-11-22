"""Exercise caption palette selection with local images and synthetic color fixtures."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from caption_colors import resolve  # noqa: E402
from media_scanner import scan, write_json  # noqa: E402
from reel_engine import build_plan  # noqa: E402

CASES = {
    "A": ("밝은 인테리어", (232, 229, 219), None, None),
    "B": ("어두운 인테리어", (41, 35, 34), None, None),
    "C": ("우드톤 주방", (156, 88, 47), "burgundy", "따뜻한 갈색 가구가 반복됩니다."),
    "D": ("식물", (25, 80, 46), "lime", "짙은 녹색 잎과 어두운 자막 영역을 확인했습니다."),
    "E": ("하늘색", (52, 117, 168), "sky-blue", "청색 계열이 면적의 대부분을 차지합니다."),
    "F": ("분홍색", (133, 56, 84), "soft-pink", "자줏빛 분홍 배경이 여러 프레임에 이어집니다."),
    "G": ("혼합 색상", (220, 210, 188), None, None),
    "H": ("블랙 직접 지정", (41, 35, 34), None, None),
    "I": ("이전 버건디 계획", (232, 229, 219), None, None),
}


def png(path, color, case):
    width, height = 216, 384
    mix = [(52, 132, 155), (221, 166, 65), (184, 77, 118), (55, 115, 60)]
    data = bytearray()
    for y in range(height):
        data.append(0)
        for x in range(width):
            source = mix[(x // 54 + y // 96) % len(mix)] if case == "G" else color
            if case == "D" and any(((x - cx) / 38) ** 2 + ((y - cy) / 72) ** 2 < 1
                                   for cx, cy in [(35, 65), (90, 140), (175, 90), (145, 220), (45, 270), (185, 338)]):
                source = (45, 112, 60)
            elif case == "E" and y < 150 and any(((x - cx) / 24) ** 2 + ((y - cy) / 9) ** 2 < 1
                                                 for cx, cy in [(56, 75), (88, 78), (155, 116)]):
                source = (202, 222, 230)
            elif case == "F" and ((x - 142) / 68) ** 2 + ((y - 50) / 100) ** 2 < 1:
                source = (166, 81, 118)
            delta = int((x - width / 2) / 12 + (y - height / 2) / 30)
            data.extend(max(0, min(255, c + delta)) for c in source)

    def chunk(kind, contents):
        return (struct.pack(">I", len(contents)) + kind + contents +
                struct.pack(">I", zlib.crc32(kind + contents)))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) +
                     chunk(b"IDAT", zlib.compress(data)) + chunk(b"IEND", b""))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--interiors", type=Path)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True)
    fixture = {"A": "01 거실.jpg", "B": "03 작업실.jpg", "C": "02 주방.jpg"}
    results = {}
    for case, (label, base, accent, reason) in CASES.items():
        directory = root / case
        directory.mkdir()
        if args.interiors and case in fixture:
            source = directory / "photo.jpg"
            shutil.copyfile(args.interiors / fixture[case], source)
            if case == "C":
                reason = "직접 확인한 목재 수납장과 따뜻한 색의 바닥이 있습니다."
        else:
            source = directory / "photo.png"
            png(source, base, case)
        args_for_plan = argparse.Namespace(
            seconds=2, fit="cover", photo_motion="none", mute_source=True, cover="storytelling",
            title="자막 컬러 테스트", hook="한글 자막의 가독성을 확인합니다", content_type="스토리텔링",
            project_id=f"caption-{case.lower()}", audience="테스트", music=None, music_volume=.23,
            source_volume=1, fade_out=0, concurrency=2, cover_photo=None, cover_video=None,
            cover_time=None, cover_native_text=False, cover_position=None, personal_style=None,
            caption_color="black" if case == "H" else "auto",
        )
        manifest = scan(directory)
        plan = build_plan(manifest, args_for_plan)
        if case == "I":
            plan.pop("captionColorMode")
        if accent:
            plan.update(planningBasis="visually-reviewed", captionAccent=accent, captionAccentReason=reason)
        write_json(directory / "reel-project.json", plan)
        assets = {entry["id"]: entry for entry in manifest["mediaAssets"]}
        report = resolve(plan, assets, {})
        assert report["sampleCount"] >= 1, report["sampleErrors"]
        assert report["minimumContrast"] >= 4.5, report
        if case in "ABG":
            assert report["captionColorPreset"] in ("white", "black")
        if case in "HI":
            assert report["captionColorPreset"] == ("black" if case == "H" else "burgundy")
        if case in "DEF":
            assert report["captionColorPreset"] == accent
        results[case] = {"title": label, "source": str(source),
                         "sourceHash": hashlib.sha256(source.read_bytes()).hexdigest(), **report}
        print(f"{case} {report['captionColorPreset']} {report['minimumContrast']}:1", flush=True)
    write_json(root / "selection-results.json", results)


if __name__ == "__main__":
    main()
