"""Sample local footage and choose one caption palette for an entire reel."""
import colorsys
import json
import math
from pathlib import Path
import statistics
import subprocess

from media_scanner import ROOT, tool

PALETTE = ROOT / "config/caption-colors.json"
CUSTOM = ROOT / "config/caption-colors.local.json"
KEYS = ("captionBackgroundColor", "captionTextColor", "captionBackgroundOpacity")
STYLE_KEYS = ("backgroundColor", "color", "backgroundOpacity")
NORMAL_MINIMUM = 4.5
SIZE = (54, 96)


def rgb(value):
    raw = bytes.fromhex(value.removeprefix("#"))
    if len(raw) != 3 or not value.startswith("#"):
        raise ValueError(f"6자리 HEX 색상을 지정하세요: {value}")
    return tuple(raw)


def palettes():
    base = json.loads(PALETTE.read_text(encoding="utf-8"))
    if CUSTOM.is_file():
        extra = json.loads(CUSTOM.read_text(encoding="utf-8-sig"))
        if not isinstance(extra, dict) or set(base) & set(extra):
            raise ValueError("개인 컬러 이름은 기본 팔레트와 달라야 합니다.")
        base.update(extra)
    for name, value in base.items():
        if not isinstance(value, dict) or any(key not in value for key in KEYS):
            raise ValueError(f"컬러 조합에 배경·글씨·불투명도를 지정하세요: {name}")
        rgb(value[KEYS[0]])
        rgb(value[KEYS[1]])
        opacity = value[KEYS[2]]
        if type(opacity) not in (int, float) or not 0 <= opacity <= 1:
            raise ValueError(f"컬러 불투명도는 0~1이어야 합니다: {name}")
    return base


def layer_settings():
    data = json.loads((ROOT / "config/presets/eunpanchi-signature.json").read_text(encoding="utf-8"))
    return data["layers"][0]


def luminance(pixel):
    def linear(x):
        x /= 255
        return x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4

    return sum(w * linear(v) for w, v in zip((.2126, .7152, .0722), pixel))


def contrast(a, b):
    low, high = sorted((a, b))
    return (high + .05) / (low + .05)


def percentile(values, fraction):
    ordered = sorted(values)
    return ordered[math.floor((len(ordered) - 1) * fraction)]


def bucket(pixel):
    hue, saturation, value = colorsys.rgb_to_hsv(*(x / 255 for x in pixel))
    if saturation < .16 or value < .14:
        return "neutral"
    degrees = hue * 360
    if 67 <= degrees < 172:
        return "green"
    if 172 <= degrees < 260:
        return "blue"
    if 285 <= degrees < 350 or (degrees >= 350 and saturation < .43 and value > .49):
        return "pink"
    if degrees >= 345 or degrees < 67:
        return "warm"
    return "other"


def distribution(pixels):
    counts = {}
    for pixel in pixels:
        family = bucket(pixel)
        counts[family] = counts.get(family, 0) + 1
    return {key: round(count / len(pixels), 4) for key, count in sorted(counts.items())}


def sample(ffmpeg, asset, clip, timestamp, layer, cue_style):
    w, h = SIZE
    if clip["fit"] == "cover":
        vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
    else:
        vf = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x101318"
    args = [ffmpeg, "-nostdin", "-v", "error", "-protocol_whitelist", "file,pipe"]
    if asset["kind"] == "video":
        args += ["-ss", f"{timestamp:.6f}"]
    args += ["-i", asset["path"], "-vf", vf, "-frames:v", "1", "-c:v", "rawvideo",
             "-threads", "1", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"]
    result = subprocess.run(args, capture_output=True, timeout=20, check=False)
    if result.returncode or len(result.stdout) != w * h * 3:
        raise RuntimeError(result.stderr.decode("utf-8", "replace").strip() or "대표 프레임을 읽을 수 없음")
    pixels = list(zip(*[iter(result.stdout)] * 3))
    center = layer["position"]
    x, y = cue_style.get("x", center["x"]), cue_style.get("y", center["y"])
    width = cue_style.get("maxWidthPx", layer["maxWidthPx"])
    roi = [pixel for i, pixel in enumerate(pixels)
           if abs((i % w + .5) * 1080 / w - x) <= width / 2
           and abs((i // w + .5) * 1920 / h - y) <= 90]
    roi = roi or pixels
    light = [luminance(p) for p in roi]
    sats = [colorsys.rgb_to_hsv(*(x / 255 for x in p))[1] for p in pixels]
    quantized = {}
    for pixel in pixels:
        key = tuple(min(255, (x // 32) * 32 + 16) for x in pixel)
        quantized[key] = quantized.get(key, 0) + 1
    dominant = sorted(quantized, key=quantized.get, reverse=True)[:3]
    summary = {"assetId": clip["assetId"], "sourceSeconds": round(timestamp, 3),
               "fit": clip["fit"], "customCrop": bool(clip.get("objectPosition")),
               "dominantColors": ["#" + bytes(p).hex().upper() for p in dominant],
               "meanLuminance": round(statistics.mean(luminance(p) for p in pixels), 4),
               "captionLuminance": round(statistics.mean(light), 4),
               "captionComplexity": round(statistics.pstdev(light), 4),
               "hues": distribution(pixels), "captionHues": distribution(roi),
               "saturation": {name: round(sum(lo <= s < hi for s in sats) / len(sats), 4)
                              for name, lo, hi in (("low", 0, .2), ("medium", .2, .55), ("high", .55, 1.01))}}
    return summary, roi


def observations(plan, assets, personal):
    ffmpeg = tool("ffmpeg")
    layer = layer_settings()
    jobs = []
    for clip in plan["clips"]:
        start = clip["timelineStartFrame"]
        end = start + clip["durationFrames"]
        for cue in plan["captions"]:
            lo, hi = max(start, cue["startFrame"]), min(end, cue["endFrame"])
            if lo >= hi:
                continue
            asset = assets[clip["assetId"]]
            style = {**personal, **cue["style"]}
            fractions = (.2, .5, .8) if asset["kind"] == "video" and hi - lo >= plan["fps"] else (.5,)
            for fraction in fractions:
                timestamp = clip["sourceStart"] + (lo - start + (hi - lo - 1) * fraction) / plan["fps"]
                jobs.append((asset, clip, timestamp if asset["kind"] == "video" else 0, style))
    if len(jobs) > 18:
        jobs = [jobs[round(i * (len(jobs) - 1) / 17)] for i in range(18)]
    result, failures = [], []
    for args in jobs:
        try:
            result.append(sample(ffmpeg, *args[:3], layer, args[3]))
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
            failures.append({"assetId": args[1]["assetId"], "error": str(error)[:300]})
    return result, failures


def evaluate(preset, records):
    box, text = rgb(preset[KEYS[0]]), luminance(rgb(preset[KEYS[1]]))
    alpha = preset[KEYS[2]]
    minima, edges = [], []
    for stat, roi in records:
        mixed = [luminance(tuple(alpha * b + (1 - alpha) * p for b, p in zip(box, pixel))) for pixel in roi]
        minima.append(min(contrast(text, p) for p in mixed))
        edges.append(statistics.mean(abs(m - luminance(p)) for m, p in zip(mixed, roi))
                     * (1 + stat["captionComplexity"] * .25))
    if not minima:
        # A manual translucent box can lie on any frame. Bound possible luminance
        # by compositing over all-black and all-white, including a possible 1:1 match.
        lo, hi = [luminance(tuple(alpha * b + (1 - alpha) * p for b in box)) for p in (0, 255)]
        minima.append(1 if lo <= text <= hi else min(contrast(text, lo), contrast(text, hi)))
    return {"minimumContrast": min(minima), "edgeScore": percentile(edges, .2) if edges else 0}


def resolve(plan, assets, personal, skip_analysis=False):
    palette = palettes()
    mode = plan.get("captionColorMode", "manual")
    key = plan.get("captionColorPreset")
    has_explicit = any(k in plan for k in KEYS)
    if key and key not in palette:
        raise ValueError(f"등록되지 않은 자막 컬러입니다: {key}")
    samples, errors = ([], []) if skip_analysis else observations(plan, assets, personal)
    stats = [s for s, _ in samples]
    metrics = {name: evaluate(value, samples) for name, value in palette.items()}
    reason = plan.get("captionColorReason")
    if mode == "manual" or has_explicit or key:
        # Missing mode is the legacy project contract.
        selected = key or ("burgundy" if "captionColorMode" not in plan else "black")
        color = {**palette[selected], **{k: plan[k] for k in KEYS if k in plan}}
        reason = reason or ("이전 프로젝트의 버건디 기본값 보존" if "captionColorMode" not in plan and not key and not has_explicit
                            else "사용자가 지정한 자막 색상 우선")
        mode = "manual"
    else:
        selected = max(("black", "white"), key=lambda name: (
            metrics[name]["minimumContrast"] >= NORMAL_MINIMUM, metrics[name]["edgeScore"],
            metrics[name]["minimumContrast"] if stats else 0))
        color = palette[selected]
        reason = ("자막 영역에서 여러 장면에 걸쳐 배경과 더 잘 구분되는 기본색"
                  if stats else "대표 프레임을 확인할 수 없어 기본 블랙 사용")
        accent = plan.get("captionAccent")
        review = plan.get("captionAccentReason")
        item = palette.get(accent, {})
        family = item.get("evidence")
        if accent and family and review and plan["planningBasis"] == "visually-reviewed" and stats and not errors:
            matches = [s["hues"].get(family, 0) for s in stats]
            stable = min(matches) >= .35 and statistics.mean(matches) >= .57
            separation = metrics[accent]["edgeScore"]
            safe = (metrics[accent]["minimumContrast"] >= max(7, NORMAL_MINIMUM)
                    and separation >= max(.28, .60 * metrics[selected]["edgeScore"])
                    and all(s["captionComplexity"] < .23 and s["fit"] != "blur" and not s["customCrop"] for s in stats))
            if stable and safe:
                selected, color = accent, item
                reason = f"실제 화면 검토와 안정적인 {family} 색상 분포가 일치하며 대비를 충족: {review}"
            else:
                reason += " · 포인트 후보는 색 분포 또는 화면 대비 기준 미충족"
    resolved = {k: color[k] for k in KEYS}
    reported_name = "custom" if has_explicit and any(resolved[k] != palette[selected][k] for k in KEYS) else selected
    personal_colors = {} if key or has_explicit else {k: personal[s] for k, s in zip(KEYS, STYLE_KEYS) if s in personal}
    effective = [{**resolved, **personal_colors,
                  **{k: cue["style"][s] for k, s in zip(KEYS, STYLE_KEYS) if s in cue["style"]}}
                 for cue in plan["captions"]]
    combos = [dict(items) for items in dict.fromkeys(tuple(pair.items()) for pair in effective)]
    candidates = combos or [resolved]
    measured = []
    for pair in candidates:
        try:
            measured.append(evaluate(pair, samples)["minimumContrast"])
        except (ValueError, TypeError):
            continue  # Legacy cue or personal overrides may use CSS color syntax.
    minimum = min(measured) if measured else None
    hues = {k: round(statistics.mean(s["hues"].get(k, 0) for s in stats), 4)
            for k in sorted({k for s in stats for k in s["hues"]})}
    return {"captionColorMode": mode, "captionColorPreset": reported_name, **resolved,
            "captionColorReason": reason, "minimumContrast": round(minimum, 2) if minimum is not None else None,
            "contrastTarget": NORMAL_MINIMUM, "warnings": [
                *(["지정 색의 예상 대비가 4.5:1보다 낮습니다."] if minimum is not None and minimum < NORMAL_MINIMUM else []),
                *(["HEX 이외의 기존 CSS 색상은 유지하며 대비 계산에서 제외했습니다."] if len(measured) < len(candidates) else []),
                *(["한 릴스에 자막 색 조합을 두 가지 이내로 사용하는 편이 좋습니다."] if len(combos) > 2 else []),
                *(["블러·사용자 지정 크롭 샘플은 근사치입니다."] if any(s["fit"] == "blur" or s["customCrop"] for s in stats) else []),
            ],
            "effectivePalettes": combos, "sampleCount": len(stats), "samples": stats, "sampleErrors": errors,
            "hueStability": {k: round(min(s["hues"].get(k, 0) for s in stats), 4) for k in hues},
            "meanHueShares": hues,
            "candidateScores": {k: {m: round(n, 4) for m, n in v.items()} for k, v in metrics.items()}}
