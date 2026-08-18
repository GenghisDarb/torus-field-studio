from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]
TOKEN_PATTERNS = (
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
)
WINDOWS_USER = re.compile(r"C:\\Users\\([^\\/\s]+)", re.IGNORECASE)
POSIX_USER = re.compile(r"/Users/([^/\s]+)")
PLACEHOLDERS = {"<user>", "$env:username", "%username%", "username"}


def main() -> int:
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).split(b"\0")
    findings: list[str] = []
    for raw_name in names:
        if not raw_name:
            continue
        relative = raw_name.decode("utf-8")
        path = ROOT / relative
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for pattern in TOKEN_PATTERNS:
            if pattern.search(text):
                findings.append(f"{relative}: credential-like token")
        for pattern, label in ((WINDOWS_USER, "Windows"), (POSIX_USER, "macOS")):
            for match in pattern.finditer(text):
                if match.group(1).casefold() not in PLACEHOLDERS:
                    findings.append(f"{relative}: local {label} user path")
    if findings:
        print("\n".join(findings))
        return 1
    print("Tracked-content credential and local-user-path scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
