"""Check or install REELS CREATOR without changing system tools."""
import argparse
import hashlib
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
NAME = "reels-creator"
MANIFEST = "release-files.txt"


def version(command, minimum=None):
    if not command:
        return None
    try:
        check = subprocess.run(command, capture_output=True, encoding="utf-8", errors="replace", timeout=15)
        lines = (check.stdout or check.stderr).splitlines()
        if check.returncode or not lines:
            return None
        match = re.search(r"\d+(?:\.\d+)+", lines[0])
        if minimum and (not match or int(match[0].split(".")[0]) < minimum):
            return None
        return lines[0]
    except (OSError, subprocess.TimeoutExpired):
        return None


def npm_command(npm_cli):
    node = shutil.which("node")
    if npm_cli:
        return [node, str(npm_cli.resolve())] if node and npm_cli.is_file() else None
    executable = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    return [executable] if executable else None


def browser_at(root, explicit):
    if explicit:
        return explicit.resolve() if explicit.is_file() else None
    env = os.environ.get("REELS_BROWSER")
    if env and Path(env).is_file():
        return Path(env).resolve()
    cache = root / "remotion/node_modules/.remotion"
    windows = cache / "chrome-headless-shell/win64/chrome-headless-shell-win64/chrome-headless-shell.exe"
    if windows.is_file():
        return windows
    return next((p for p in cache.rglob("chrome-headless-shell") if p.is_file()), None)


def check_tools(npm):
    if platform.system() == "Darwin":
        release = platform.mac_ver()[0]
        print(f"macOS: {release} (15 이상 필요)")
        if not release or int(release.split(".")[0]) < 15:
            raise RuntimeError("Remotion은 macOS 15 이상이 필요합니다.")
    checks = [
        ("Python", [sys.executable, "--version"], 3, "https://www.python.org/downloads/"),
        ("Node.js", command("node", "--version"), 22, "https://nodejs.org/en/download"),
        ("npm", [*npm, "--version"] if npm else None, 10, "Node.js 설치 확인"),
        ("FFmpeg", command("ffmpeg", "-version"), None, "https://ffmpeg.org/download.html"),
        ("ffprobe", command("ffprobe", "-version"), None, "https://ffmpeg.org/download.html"),
        ("Git", command("git", "--version"), None, "https://git-scm.com/downloads"),
    ]
    missing = []
    for label, cmd, minimum, help_url in checks:
        result = version(cmd, minimum)
        if label == "Python" and sys.version_info < (3, 10):
            result = None
        print(f"{label}: {result or '확인 필요 — ' + help_url}", flush=True)
        if result is None and label != "Git":
            missing.append(label)
    codex = shutil.which("codex")
    print(f"Codex CLI: {codex or 'PATH에 없음. Codex 앱 사용 시 선택 사항'}", flush=True)
    return missing


def command(name, flag):
    path = shutil.which(name)
    return [path, flag] if path else None


def checked_files():
    paths = ROOT.joinpath(MANIFEST).read_text(encoding="utf-8").splitlines()
    if not paths or "SKILL.md" not in paths or len(paths) != len(set(paths)):
        raise RuntimeError("배포 파일 목록이 올바르지 않습니다.")
    for name in paths:
        relative = Path(name)
        path = ROOT / relative
        if relative.is_absolute() or ".." in relative.parts or path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT):
            raise RuntimeError(f"배포 파일 확인 실패: {name}")
        yield relative


def copy_release(dest):
    files = list(checked_files())
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_symlink():
        raise RuntimeError("설치 대상으로 심볼릭 링크를 사용할 수 없습니다.")
    if dest.exists():
        marker = dest / MANIFEST
        if not marker.is_file() or marker.is_symlink() or marker.read_bytes() != (ROOT / MANIFEST).read_bytes():
            raise RuntimeError("다른 설치가 있습니다. 해당 폴더를 보존하고 다른 --skills-dir을 사용하세요.")
    else:
        dest.mkdir()
        with (dest / MANIFEST).open("xb") as target:
            target.write((ROOT / MANIFEST).read_bytes())
    for relative in files:
        target = dest / relative
        if not target.resolve().is_relative_to(dest.resolve()) or target.is_symlink():
            raise RuntimeError(f"설치 파일 경로를 확인하세요: {relative}")
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            with (ROOT / relative).open("rb") as source, target.open("xb") as file:
                shutil.copyfileobj(source, file)
    print(f"스킬 설치 경로: {dest}", flush=True)


def install_dependencies(dest, npm):
    project = dest / "remotion"
    modules = project / "node_modules"
    lock = project / "package-lock.json"
    fingerprint = hashlib.sha256(lock.read_bytes()).hexdigest()
    marker = project / ".dependencies-installed"
    if modules.exists():
        if marker.is_file() and marker.read_text(encoding="utf-8") == fingerprint and \
                (modules / "@remotion/cli/package.json").is_file():
            print("npm 의존성 재사용", flush=True)
            return
        raise RuntimeError("기존 node_modules를 보존했습니다. 깨끗한 설치 경로를 지정하세요.")
    if marker.exists():
        raise RuntimeError("설치 표시와 node_modules 상태가 다릅니다. 별도 설치 경로를 사용하세요.")
    env = {**os.environ, "NPM_CONFIG_UPDATE_NOTIFIER": "false",
           "NPM_CONFIG_CACHE": str(dest / ".local-tools/npm-cache")}
    print("npm 잠금 파일의 패키지를 공식 레지스트리에서 설치합니다.", flush=True)
    subprocess.run([*npm, "ci", "--include=dev", "--ignore-scripts", "--no-audit", "--no-fund",
                    "--registry=https://registry.npmjs.org/"], cwd=project, env=env, check=True)
    with marker.open("x", encoding="utf-8") as file:
        file.write(fingerprint)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-dir", type=Path, default=Path.home() / ".agents" / "skills")
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--dependencies", action="store_true", help="opt in to npm downloads")
    parser.add_argument("--install-browser", action="store_true", help="opt in to Chromium download if missing")
    parser.add_argument("--browser", type=Path, help="existing browser executable")
    parser.add_argument("--npm-cli", type=Path, help="optional npm-cli.js path")
    args = parser.parse_args()
    npm = npm_command(args.npm_cli)
    dest = args.skills_dir.expanduser().resolve() / NAME
    print(f"Codex 사용자 스킬 경로: {dest}", flush=True)
    missing = check_tools(npm)
    if not args.install:
        browser = browser_at(dest, args.browser)
        print(f"설치 상태: {'SKILL.md 확인' if (dest / 'SKILL.md').is_file() else '설치 전'}")
        print(f"렌더 브라우저: {browser or '설치 또는 기존 경로 지정 필요'}")
        return int(bool(missing))
    if missing:
        raise RuntimeError("먼저 준비가 필요한 도구: " + ", ".join(missing))
    if args.browser and not args.browser.is_file():
        raise RuntimeError("--browser 경로에 실행 파일이 없습니다.")
    copy_release(dest)
    if args.dependencies:
        install_dependencies(dest, npm)
    browser = browser_at(dest, args.browser)
    if not browser and args.install_browser:
        project = dest / "remotion"
        cli = project / "node_modules/@remotion/cli/remotion-cli.js"
        if not cli.is_file():
            raise RuntimeError("Chromium을 준비하기 전에 npm 의존성을 설치하세요.")
        print("Remotion Chrome Headless Shell을 준비합니다.", flush=True)
        subprocess.run([shutil.which("node"), str(cli), "browser", "ensure"], cwd=project, check=True)
        browser = browser_at(dest, args.browser)
        if not browser:
            raise RuntimeError("렌더 브라우저를 찾을 수 없습니다. --browser 경로를 지정하세요.")
    print(f"렌더 브라우저: {browser or '준비 필요. --install-browser 또는 --browser 사용'}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        sys.exit(f"[install] {error}")
