import glob
import platform
import re
import subprocess


def parse_unity_log(log_content: str) -> dict:
    errors = []
    warnings = []
    for line in log_content.splitlines():
        if re.search(r"Compiler error|CS\d{4}", line):
            errors.append(line.strip()[:200])
        elif "Exception" in line and ("import" in line.lower() or "compile" in line.lower()):
            errors.append(line.strip()[:200])
        elif "MissingReferenceException" in line or "NullReferenceException" in line:
            errors.append(line.strip()[:200])
        elif "warning CS" in line:
            warnings.append(line.strip()[:200])
    return {"errors": errors, "warnings": warnings}


def process_output_summary(result: subprocess.CompletedProcess) -> str:
    parts = []
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    if stdout:
        parts.append(f"stdout: {stdout[:200]}")
    if stderr:
        parts.append(f"stderr: {stderr[:200]}")
    return " (" + "; ".join(parts) + ")" if parts else ""


def find_unity_executable(unity_config: dict) -> str | None:
    exe = unity_config.get("executable", "auto")
    if exe != "auto":
        return exe
    system = platform.system()
    if system == "Windows":
        paths = [
            r"C:\Program Files\Unity\Hub\Editor\*\Editor\Unity.exe",
            r"C:\Program Files\Unity\Hub\Editor\*\Editor\Data\PlaybackEngines\*\Unity.exe",
        ]
    elif system == "Darwin":
        paths = [
            "/Applications/Unity/Hub/Editor/*/Unity.app/Contents/MacOS/Unity",
        ]
    else:
        paths = [
            "/opt/unity/Editor/Unity",
            "/usr/bin/unity",
        ]
    for pattern in paths:
        matches = glob.glob(pattern)
        if matches:
            return sorted(matches)[-1]
    return None
