"""Build, validate, and render a local reel."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory
from local_media import serve_media

from media_scanner import IMAGES, ROOT, VIDEOS, inspect, probe, run, scan, tool, write_json
from caption_colors import KEYS as COLOR_KEYS, STYLE_KEYS as COLOR_STYLE_KEYS, palettes, resolve as resolve_colors

REMOTION = ROOT / "remotion"
TYPES = ("정보형", "스토리텔링", "브이로그", "제품 리뷰", "인테리어 비포애프터")
COVERS = ("bold-hook", "storytelling", "playful-impact")
LAYERS = {
    "bold-hook": {"title", "subtitle"},
    "storytelling": {"title"},
    "playful-impact": {"lead-1", "lead-2", "lead-3", "keyword"},
}
FPS = 30
REFERENCE_FOLDER = (ROOT / "references" / "user-samples").resolve()
PERSONAL_STYLES = ROOT / "config" / "presets" / "custom"


def fail(condition, message):
    if not condition:
        raise ValueError(message)


def frames(seconds):
    return math.floor(seconds * FPS + 0.5)


def personal_style_path(name, style_root=PERSONAL_STYLES):
    fail(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,59}", name) is not None, "개인 프리셋 이름은 영문 소문자·숫자·하이픈을 사용하세요.")
    return style_root / f"{name}.json"


def read_personal_style(name, style_root=PERSONAL_STYLES):
    if not name:
        return {}
    path = personal_style_path(name, style_root)
    fail(path.is_file(), f"개인 프리셋 {name}이 없습니다. save-style로 먼저 등록하세요.")
    run([node(), REMOTION / "validate-plan.cjs", path, "--style"], timeout=30)
    return json.loads(path.read_text(encoding="utf-8-sig"))


def cover_text(title, preset):
    if preset == "playful-impact":
        return {"lead-1": "오늘의", "lead-2": "작은", "lead-3": "이야기", "keyword": title}
    return {"title": title}


def select_cover(assets, clips, args):
    if args.cover_time is not None:
        fail(args.cover_video is not None and math.isfinite(args.cover_time) and args.cover_time >= 0,
             "--cover-time에는 --cover-video와 함께 0 이상의 초를 입력하세요.")
    selected = args.cover_photo or args.cover_video
    if selected:
        path = selected.resolve()
        is_photo = args.cover_photo is not None
        supported = IMAGES if is_photo else VIDEOS
        fail(path.is_file() and path.suffix.lower() in supported and not path.is_relative_to(REFERENCE_FOLDER),
             f"표지로 사용할 수 있는 별도의 {'사진' if is_photo else '영상'}을 선택하세요: {path}")
        info = next((asset for asset in assets if Path(asset["path"]) == path), None)
        if info is None:
            info = inspect(path, path.name, tool("ffprobe"), tool("ffmpeg"))
            fail(not info["error"], f"표지 파일을 읽을 수 없습니다: {info['error']}")
            info["id"] = "m-" + hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:16]
            assets.append(info)
        return info["id"], 0 if is_photo else args.cover_time or 0, "user-photo" if is_photo else "user-video-frame"

    by_id = {asset["id"]: asset for asset in assets}
    first_photo = next((clip for clip in clips if by_id[clip["assetId"]]["kind"] == "image"), None)
    if first_photo:
        return first_photo["assetId"], 0, "first-usable-photo"
    first = clips[0]
    return first["assetId"], first["sourceStart"], "first-usable-video-frame"


def build_plan(manifest, args, style_root=PERSONAL_STYLES):
    assets = [a for a in manifest["mediaAssets"] if a["error"] is None and
              not Path(a["path"]).resolve().is_relative_to(REFERENCE_FOLDER)]
    fail(bool(assets), "제작용 사진·영상을 찾지 못했습니다. 레퍼런스 외에 사용할 미디어와 표지를 선택해 주세요.")
    target = frames(args.seconds)
    fail(2 <= target <= FPS * 600, "길이는 2~18000프레임으로 지정하세요.")
    assets = assets[:target]
    capacities = [target if a["kind"] == "image" else math.floor(a["duration"] * FPS + 1e-7) for a in assets]
    fail(sum(capacities) >= target, "원본 길이 합계가 부족합니다. 목표 시간을 줄이거나 사진·영상을 추가하세요.")
    durations = [0] * len(assets)
    remaining = target
    while remaining:
        active = [i for i, cap in enumerate(capacities) if durations[i] < cap]
        share = max(1, remaining // len(active))
        for i in active:
            add = min(share, capacities[i] - durations[i], remaining)
            durations[i] += add
            remaining -= add

    clips = []
    cursor = 0
    for asset, duration in zip(assets, durations):
        if not duration:
            continue
        movie = asset["kind"] == "video"
        clips.append({"assetId": asset["id"], "sourceStart": 0, "sourceEnd": duration / FPS,
                      "timelineStartFrame": cursor, "durationFrames": duration, "fit": args.fit,
                      "useSourceAudio": movie and asset["hasAudio"] and not args.mute_source,
                      "motion": args.photo_motion if not movie else "none", "purpose": asset["filename"]})
        cursor += duration
    hook = args.hook or args.title
    personal = read_personal_style(args.personal_style, style_root)
    cover = args.cover or personal.get("cover", {}).get("preset") or ("bold-hook" if args.content_type == "정보형" else
                           "playful-impact" if args.content_type == "인테리어 비포애프터" else "storytelling")
    cover_id, cover_time, selection = select_cover(assets, clips, args)
    cover_settings = {
        "preset": cover, "text": {} if args.cover_native_text else cover_text(args.title, cover),
        "assetId": cover_id, "sourceTime": cover_time, "selection": selection,
    }
    if args.cover_position:
        cover_settings["objectPosition"] = args.cover_position
    hook_end = min(3 * FPS, target)
    captions = [{"text": hook, "startFrame": 0, "endFrame": hook_end, "style": {}}]
    for clip in clips:
        start = max(hook_end, clip["timelineStartFrame"])
        end = clip["timelineStartFrame"] + clip["durationFrames"]
        if start < end:
            title = Path(clip["purpose"]).stem
            captions.append({"text": title, "startFrame": start, "endFrame": end, "style": {}})
    return {"schemaVersion": 1, "projectId": args.project_id, "title": args.title,
            "captionColorMode": "auto" if args.caption_color == "auto" else "manual",
            **({"captionColorPreset": args.caption_color} if args.caption_color != "auto" else {}),
            **({"personalStyle": args.personal_style} if args.personal_style else {}),
            "targetDuration": target / FPS, "fps": FPS, "resolution": {"width": 1080, "height": 1920},
            "contentType": args.content_type, "targetAudience": args.audience, "planningBasis": "file-order",
            "story": ["첫 3초 제목", "파일명 순서에 따른 장면 전개", "마지막 장면으로 마무리"],
            "hook": {"text": hook, "endFrame": hook_end},
            "cover": cover_settings,
            "preset": "eunpanchi-signature",
            "mediaAssets": [{k: a[k] for k in ("id", "path", "kind")} for a in assets],
            "clips": clips, "captions": captions,
            "audioSettings": {"sourceVolume": args.source_volume, "musicPath": str(args.music.resolve()) if args.music else None,
                              "musicVolume": args.music_volume, "fadeOutFrames": args.fade_out},
            "renderSettings": {"codec": "h264", "concurrency": args.concurrency}}


def node():
    executable = shutil.which("node")
    fail(executable is not None, "Node.js 실행 파일이 필요합니다.")
    return executable


def read_plan(path):
    run([node(), REMOTION / "validate-plan.cjs", path], timeout=30)
    return json.loads(path.read_text(encoding="utf-8-sig"))


def validate_plan(plan, manifest=None, input_root=None, style_root=PERSONAL_STYLES):
    palette = palettes()
    for field in ("captionColorPreset", "captionAccent"):
        if plan.get(field):
            fail(plan[field] in palette, f"등록되지 않은 자막 컬러입니다: {plan[field]}")
    ffprobe, ffmpeg = tool("ffprobe"), tool("ffmpeg")
    cached = {a["path"]: a for a in (manifest or {}).get("mediaAssets", [])}
    assets = {}
    for a in plan["mediaAssets"]:
        fail(a["id"] not in assets, f"중복 미디어 ID: {a['id']}")
        path = Path(a["path"])
        check_location(path, input_root)
        fail(path.is_absolute() and path.is_file(), f"미디어 경로를 확인하세요: {path}")
        fail(not path.resolve().is_relative_to(REFERENCE_FOLDER), f"스타일 레퍼런스 대신 제작용 미디어를 선택하세요: {path}")
        fail(path.suffix.lower() in IMAGES | VIDEOS, f"지원하는 확장자를 사용하세요: {path.name}")
        info = cached.get(str(path)) or inspect(path, path.name, ffprobe, ffmpeg)
        fail(not info["error"], f"{path.name}: {info['error']}")
        fail(a["kind"] == info["kind"], f"미디어 종류가 일치하지 않습니다: {path.name}")
        assets[a["id"]] = info

    total = frames(plan["targetDuration"])
    fail(abs(total / FPS - plan["targetDuration"]) < 1e-6, "목표 길이를 30fps 프레임 단위로 맞추세요.")
    cursor = 0
    for i, clip in enumerate(plan["clips"], 1):
        info = assets.get(clip["assetId"])
        fail(info is not None, f"컷 {i}: 존재하는 미디어 ID를 지정하세요.")
        start, end = clip["sourceStart"], clip["sourceEnd"]
        fail(clip["timelineStartFrame"] == cursor, f"컷 {i}: timelineStartFrame을 {cursor}로 맞추세요.")
        fail(end > start and frames(end) - frames(start) == clip["durationFrames"] and
             abs(start - frames(start)/FPS) < 1e-6 and abs(end - frames(end)/FPS) < 1e-6,
             f"컷 {i}: 원본 시간은 1/30초 단위이고 구간 프레임 수와 durationFrames가 같아야 합니다.")
        if info["kind"] == "video":
            last = math.floor(info["duration"] * FPS + 1e-7)
            fail(frames(end) <= last,
                 f"컷 {i}: 원본 영상 길이 {info['duration']:.3f}초를 초과합니다. sourceEnd를 {last/FPS:.6f}초 이하로 줄이고 durationFrames·후속 시작 프레임·자막·목표 길이를 함께 조정하세요.")
            fail(clip["motion"] == "none", f"컷 {i}: 팬·줌은 사진에만 지정하세요.")
        else:
            fail(not clip["useSourceAudio"] and start == 0, f"컷 {i}: 사진은 sourceStart=0, useSourceAudio=false여야 합니다.")
        cursor += clip["durationFrames"]
    fail(cursor == total, f"컷 합계 {cursor}프레임과 목표 {total}프레임이 다릅니다.")
    fail(plan["hook"]["endFrame"] <= min(3 * FPS, total), "훅 끝 프레임은 첫 3초 안이어야 합니다.")

    last = 0
    for i, cue in enumerate(plan["captions"], 1):
        fail(last <= cue["startFrame"] < cue["endFrame"] <= total,
             f"자막 {i}: 시간순으로 정렬하고 서로 겹치지 않게 영상 범위 안에 배치하세요.")
        last = cue["endFrame"]
    cover = plan["cover"]
    info = assets.get(cover["assetId"])
    fail(info is not None, "표지에 존재하는 미디어 ID를 지정하세요.")
    good_time = cover["sourceTime"] == 0 if info["kind"] == "image" else cover["sourceTime"] < info["duration"]
    fail(good_time, "표지 sourceTime을 원본 범위 안으로 조정하세요. 사진에는 0을 사용합니다.")
    allowed = LAYERS[cover["preset"]]
    personal_cover = read_personal_style(plan.get("personalStyle"), style_root).get("cover", {})
    if personal_cover.get("preset", cover["preset"]) == cover["preset"]:
        fail(set(personal_cover.get("layers", {})) <= allowed, "개인 스타일에 현재 표지 프리셋과 맞지 않는 레이어가 있습니다.")
    required = "keyword" if cover["preset"] == "playful-impact" else "title"
    fail((not cover["text"] or required in cover["text"]) and
         (set(cover["text"]) | set(cover.get("overrides", {}))) <= allowed,
         f"표지 문구에 {required}를 포함하고 프리셋에 정의된 레이어 ID만 사용하세요.")
    music = plan["audioSettings"]["musicPath"]
    if music:
        path = Path(music)
        check_location(path, input_root)
        fail(path.is_absolute() and path.is_file(), f"배경음악 경로를 확인하세요: {path}")
        fail(any(s["codec_type"] == "audio" for s in probe(path, ffprobe)["streams"]), "배경음악에 오디오 스트림이 없습니다.")
    return assets


def allocate(project_id, output_root):
    fail(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,59}", project_id) is not None, "projectId는 영문 소문자·숫자·하이픈으로 지정하세요.")
    root = output_root.resolve()
    project = root / project_id
    project.mkdir(parents=True, exist_ok=True)
    fail(project.resolve() == project, f"출력 프로젝트 폴더가 다른 경로를 가리킵니다: {project}")
    for number in range(1, 100000):
        version = project / f"v{number:03d}"
        try:
            version.mkdir()
            return version
        except FileExistsError:
            continue
    raise ValueError("출력 버전 번호를 할당할 수 없습니다.")


def stage_media(plan, assets, public, register, cover_only=False, style_root=PERSONAL_STYLES):
    ffmpeg = tool("ffmpeg")
    media = public / "engine-media"
    media.mkdir(parents=True)
    paths = {}
    used = () if cover_only else dict.fromkeys(clip["assetId"] for clip in plan["clips"])
    for asset_id in used:
        info = assets[asset_id]
        path = Path(info["path"])
        if info["kind"] == "image":
            paths[asset_id] = register(path)
        else:
            # OffthreadVideo caches its input. Feed it a temporary encode, never the original.
            end = max(clip["sourceEnd"] for clip in plan["clips"] if clip["assetId"] == asset_id)
            proxy = media / f"{asset_id}.mp4"
            run([ffmpeg, "-nostdin", "-v", "error", "-protocol_whitelist", "file", "-i", path, "-t", end + 1 / FPS,
                 "-map", "0:V:0", "-map", "0:a:0?", "-map_metadata", "-1", "-map_chapters", "-1",
                 "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-c:v", "libx264", "-crf", "16", "-preset", "fast",
                 "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", proxy], timeout=1800)
            paths[asset_id] = "engine-media/" + proxy.name

    # Preserve locally configured font support without staging unrelated public assets.
    fonts = REMOTION / "public" / "fonts"
    if fonts.is_dir():
        shutil.copytree(fonts, public / "fonts", ignore=lambda _, names: [
            name for name in names if Path(name).suffix.lower() not in {".woff", ".woff2", ".ttf", ".otf"}
        ])

    cover = plan["cover"]
    source = assets[cover["assetId"]]
    cover_name = "cover-source.png"
    if source["kind"] == "image":
        cover_path = register(Path(source["path"]))
    else:
        run([ffmpeg, "-nostdin", "-v", "error", "-ss", cover["sourceTime"], "-protocol_whitelist", "file",
             "-i", source["path"], "-map", "0:V:0", "-frames:v", "1", media / cover_name], timeout=120)
        fail((media / cover_name).is_file(), "표지 프레임을 추출할 수 없습니다. sourceTime을 앞쪽으로 조정하세요.")
        cover_path = "engine-media/" + cover_name

    music = None if cover_only else plan["audioSettings"]["musicPath"]
    if music:
        run([ffmpeg, "-nostdin", "-v", "error", "-protocol_whitelist", "file", "-i", music, "-map", "0:a:0",
             "-t", plan["targetDuration"], "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2",
             media / "music.wav"], timeout=180)
    return {"plan": plan, "assetPaths": paths, "coverPath": cover_path,
            "personalStyle": read_personal_style(plan.get("personalStyle"), style_root), "coverOnly": cover_only,
            "musicPath": "engine-media/music.wav" if music else None}


def verify_cover(version, plan):
    size = plan["resolution"]
    with (version / "cover.png").open("rb") as file:
        header = file.read(24)
    fail(header[:16] == b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" and
         struct.unpack(">II", header[16:24]) == (size["width"], size["height"]), "표지 PNG 크기 또는 형식이 올바르지 않습니다.")
    return {**size, "coverFormat": "png"}


def verify(version, plan, expect_audio):
    report = probe(version / "reel.mp4", tool("ffprobe"))
    video = next(s for s in report["streams"] if s["codec_type"] == "video")
    audio = any(s["codec_type"] == "audio" for s in report["streams"])
    size = plan["resolution"]
    count = frames(plan["targetDuration"])
    fail(video["codec_name"] == "h264" and video["width"] == size["width"] and video["height"] == size["height"] and
         video["avg_frame_rate"] == "30/1" and int(video.get("nb_frames", 0)) == count and
         abs(float(video["duration"]) - count / FPS) < 1 / FPS and audio == expect_audio,
         "영상 메타데이터가 렌더 설정과 일치하지 않습니다.")
    return {"codec": "h264", **verify_cover(version, plan), "fps": FPS, "frames": count,
            "videoSeconds": float(video["duration"]), "containerSeconds": float(report["format"]["duration"]),
            "hasAudio": audio, "coverFormat": "png"}


def render(plan_path, output_root, manifest=None, browser=None, existing_version=None, cover_only=False,
           projects_root=None, input_root=None, style_root=PERSONAL_STYLES):
    stage = "validate"
    version = existing_version
    try:
        plan = read_plan(plan_path)
        assets = validate_plan(plan, manifest, input_root, style_root)
        version = version or allocate(plan["projectId"], output_root)
        records = version
        if projects_root:
            records = plan_path.parent if manifest is not None else allocate(plan["projectId"], projects_root)
        if records / "reel-project.json" != plan_path:
            write_json(records / "reel-project.json", plan)
        if not (records / "media-manifest.json").exists():
            write_json(records / "media-manifest.json", manifest or {
                "schemaVersion": 1, "inputRoot": None, "analysisMode": "metadata-and-first-frame-decode",
                "mediaAssets": [{**info, "id": asset_id} for asset_id, info in assets.items()],
            })
        stage = "stage-media"
        color_report = None
        if not cover_only:
            personal = read_personal_style(plan.get("personalStyle"), style_root).get("caption", {})
            color_report = resolve_colors(plan, assets, personal)
            write_json(records / "caption-color-report.json", color_report)
            print(f"[caption-color] {color_report['captionColorPreset']} · {color_report['captionColorReason']}", flush=True)
        write_json(records / "captions.json", plan["captions"])
        expect_audio = bool(plan["audioSettings"]["musicPath"] or any(
            c["useSourceAudio"] and assets[c["assetId"]]["hasAudio"] for c in plan["clips"]))
        with TemporaryDirectory(prefix="render-", dir=version) as temp, serve_media() as register:
            work = Path(temp)
            props = stage_media(plan, assets, work / "public", register, cover_only, style_root)
            if color_report:
                props["captionColors"] = {s: color_report[k] for k, s in zip(COLOR_KEYS, COLOR_STYLE_KEYS)}
                if plan.get("captionColorPreset") or any(k in plan for k in COLOR_KEYS):
                    caption = props["personalStyle"].get("caption", {})
                    props["personalStyle"]["caption"] = {k: v for k, v in caption.items() if k not in COLOR_STYLE_KEYS}
            props["expectAudio"] = expect_audio
            write_json(work / "props.json", props)
            stage = "remotion"
            command = [node(), REMOTION / "render-reel.cjs", work, version]
            if browser:
                command.append(str(browser.resolve()))
            subprocess.run(list(map(str, command)), cwd=REMOTION, check=True)
        stage = "verify"
        metadata = verify_cover(version, plan) if cover_only else verify(version, plan, expect_audio)
        if cover_only:
            metadata["coverOnly"] = True
        write_json(version / "render-report.json", {"status": "success", "stage": stage,
                                                      "projectPlan": str(records / "reel-project.json"), **metadata})
        print(f"[project] {records}", flush=True)
        print(f"[done] {version}", flush=True)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, StopIteration, KeyError) as error:
        if version:
            write_json(version / "render-report.json", {"status": "failed", "stage": stage, "error": str(error)})
        raise RuntimeError(f"[{stage}] {error}") from error


def check_location(path, root):
    if root is not None:
        fail(path.resolve().is_relative_to(root), f"허용된 작업 폴더 ({root})의 경로를 사용하세요: {path}")


def workspace_paths(path):
    root = path.resolve()
    fail(not root.drive.startswith("\\\\"), "네트워크 공유 대신 로컬 작업 폴더를 사용하세요.")
    fail(not root.is_relative_to(ROOT) and not any((ancestor / ".git").exists()
         for ancestor in (root, *root.parents)), "작업 공간은 프로그램 및 Git 저장소 밖에 지정하세요.")
    folders = [root / name for name in ("input", "output", "projects")]
    for folder in folders:
        fail(folder.resolve() == folder and not ROOT.is_relative_to(folder) and not (folder / ".git").exists(),
             f"작업 폴더는 별도의 로컬 폴더여야 합니다: {folder}")
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)
    return folders


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, help="Local workspace outside the program and Git repositories")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Create input, output and projects folders")
    for name in ("plan", "auto"):
        command = sub.add_parser(name)
        command.add_argument("folder", type=Path, nargs="?")
        command.add_argument("--project-id", required=True)
        command.add_argument("--title", required=True)
        command.add_argument("--seconds", type=float, default=30)
        command.add_argument("--hook")
        command.add_argument("--audience", default="릴스 시청자")
        command.add_argument("--content-type", choices=TYPES, default="스토리텔링")
        command.add_argument("--cover", choices=COVERS)
        command.add_argument("--cover-photo", type=Path)
        command.add_argument("--cover-video", type=Path)
        command.add_argument("--cover-time", type=float)
        command.add_argument("--cover-position")
        command.add_argument("--cover-native-text", action="store_true")
        command.add_argument("--personal-style")
        command.add_argument("--caption-color", default="auto", help="auto or a caption palette ID")
        command.add_argument("--fit", choices=("cover", "contain", "blur"), default="cover")
        command.add_argument("--photo-motion", choices=("none", "push-in", "pan-left", "pan-right"), default="push-in")
        command.add_argument("--mute-source", action="store_true")
        command.add_argument("--source-volume", type=float, default=1)
        command.add_argument("--music", type=Path)
        command.add_argument("--music-volume", type=float, default=.23)
        command.add_argument("--fade-out", type=int, default=18)
        command.add_argument("--concurrency", type=int, default=2)
    for name in ("render", "validate"):
        sub.add_parser(name).add_argument("plan", type=Path)
    sub.choices["render"].add_argument("--cover-only", action="store_true")
    save = sub.add_parser("save-style")
    save.add_argument("name")
    save.add_argument("source", type=Path)
    for name in ("plan", "auto", "render"):
        sub.choices[name].add_argument("--output", type=Path, default=None)
        sub.choices[name].add_argument("--browser", type=Path)
    args = parser.parse_args()
    stage = "scan"
    try:
        input_root = projects_root = None
        args.style_root = PERSONAL_STYLES
        if args.workspace:
            stage = "workspace"
            fail(getattr(args, "output", None) is None, "--workspace와 --output은 함께 지정할 수 없습니다.")
            input_root, args.output, projects_root = workspace_paths(args.workspace)
            args.style_root = projects_root / "presets"
            fail(args.style_root.resolve() == args.style_root, "개인 프리셋 폴더가 다른 경로를 가리킵니다.")
        elif hasattr(args, "output"):
            stage = "workspace"
            fail(args.output is not None, "실제 제작은 --workspace를 지정하세요. 기존 테스트 모드는 --output이 필요합니다.")
        if args.command == "init":
            fail(input_root is not None, "--workspace로 작업 폴더를 지정하세요.")
            print(f"[workspace] {input_root.parent}", flush=True)
            return
        stage = "scan"
        if args.command in {"auto", "plan"}:
            folder = args.folder or input_root
            fail(folder is not None, "입력 폴더 또는 --workspace를 지정하세요.")
            for path in (folder, args.cover_photo, args.cover_video, args.music):
                if path is not None:
                    check_location(path, input_root)
            fail(math.isfinite(args.seconds), "유한한 초 단위 길이를 입력하세요.")
            manifest = scan(folder)
            stage = "plan"
            version = allocate(args.project_id, projects_root or args.output)
            manifest_path = version / "media-manifest.json"
            write_json(manifest_path, manifest)
            path = version / "reel-project.json"
            write_json(path, build_plan(manifest, args, args.style_root))
            if args.command == "auto":
                render(path, args.output, manifest, args.browser, None if projects_root else version,
                       projects_root=projects_root, input_root=input_root, style_root=args.style_root)
            else:
                validate_plan(read_plan(path), manifest, input_root, args.style_root)
                print(f"[plan] {path}", flush=True)
        elif args.command == "validate":
            stage = "validate"
            check_location(args.plan, projects_root)
            validate_plan(read_plan(args.plan), input_root=input_root, style_root=args.style_root)
            print("[validate] OK", flush=True)
        elif args.command == "save-style":
            stage = "save-style"
            run([node(), REMOTION / "validate-plan.cjs", args.source, "--style"], timeout=30)
            dest = personal_style_path(args.name, args.style_root)
            dest.parent.mkdir(parents=True, exist_ok=True)
            write_json(dest, json.loads(args.source.read_text(encoding="utf-8-sig")))
            print(f"[save-style] {dest}", flush=True)
        else:
            check_location(args.plan, projects_root)
            render(args.plan.resolve(), args.output, browser=args.browser, cover_only=args.cover_only,
                   projects_root=projects_root, input_root=input_root, style_root=args.style_root)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        message = str(error)
        tagged = ("[validate]", "[stage-media]", "[remotion]", "[verify]")
        sys.exit(message if message.startswith(tagged) else f"[{stage}] {message}")


if __name__ == "__main__":
    main()
