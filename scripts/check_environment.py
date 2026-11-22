"""Report the local tools and validate the starter preset."""
import json
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    print(f"Python {sys.version.split()[0]} ({sys.executable})", flush=True)
    preset = json.loads(
        (ROOT / "config" / "presets" / "default.json").read_text(encoding="utf-8")
    )
    print(f"Preset: {preset['id']} ({preset['canvas']})", flush=True)
    node = shutil.which("node")
    npm = shutil.which("npm")
    local_npm = ROOT / ".local-tools" / "npm" / "package" / "bin" / "npm-cli.js"
    bundled_tools = ROOT / "remotion" / "node_modules"
    npm_command = [npm, "--version"] if npm else None
    if node and local_npm.is_file():
        npm_command = [node, str(local_npm), "--version"]
    tools = {
        "node": [node, "--version"] if node else None,
        "npm": npm_command,
    }
    for name in ("ffmpeg", "ffprobe"):
        executable = shutil.which(name)
        if executable is None and sys.platform == "win32":
            candidates = bundled_tools.glob(
                f".pnpm/@remotion+compositor-win32-*/node_modules/@remotion/compositor-win32-*/{name}.exe"
            )
            bundled = next((path for path in candidates if path.is_file()), None)
            executable = str(bundled) if bundled else None
        tools[name] = [executable, "-version"] if executable else None

    healthy = True
    for name, command in tools.items():
        if command is None:
            print(f"{name}: unavailable on PATH or in project tools", flush=True)
            healthy = False
            continue
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=15, errors="replace"
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            print(f"{name}: {error}", flush=True)
            healthy = False
            continue
        lines = (result.stdout or result.stderr).splitlines()
        version = lines[0] if lines else "no output"
        print(f"{name}: {version} (exit {result.returncode})", flush=True)
        healthy &= result.returncode == 0
    return 0 if healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())
