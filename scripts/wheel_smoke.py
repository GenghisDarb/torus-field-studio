from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

ROOT = Path(__file__).parents[1]


def run(*arguments: str) -> None:
    subprocess.run(arguments, cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Install and smoke-test the built TORUS wheel")
    parser.add_argument("--wheel-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--digest", type=Path, required=True)
    args = parser.parse_args()
    wheels = sorted(args.wheel_dir.glob("torusbrot-*.whl"))
    if len(wheels) != 1:
        raise ValueError(f"Expected exactly one wheel, found {len(wheels)}")

    with tempfile.TemporaryDirectory(prefix="torusbrot-wheel-smoke-") as temporary:
        directory = Path(temporary)
        environment = directory / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        scripts = environment / ("Scripts" if sys.platform == "win32" else "bin")
        python = scripts / ("python.exe" if sys.platform == "win32" else "python")
        executable = scripts / ("torusbrot.exe" if sys.platform == "win32" else "torusbrot")
        run(
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            str(wheels[0].resolve()),
        )
        if not executable.exists():
            raise ValueError("The wheel did not install the torusbrot console script")
        run(str(executable), "--help")

        specification = json.loads(
            (ROOT / "examples/tld-parent-null/run-spec.json").read_text(encoding="utf-8")
        )
        specification["grid"] = {"width": 8, "height": 6}
        specification_path = directory / "run-spec.json"
        specification_path.write_text(
            json.dumps(specification, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        outputs = [directory / "first.tbx.zip", directory / "second.tbx.zip"]
        for output in outputs:
            run(
                str(executable),
                "generate",
                "local",
                "--spec",
                str(specification_path),
                "--domain",
                str(ROOT / "examples/tld-parent-null/domain.json"),
                "--output",
                str(output),
            )
            run(str(executable), "audit", str(output))
        payloads = [output.read_bytes() for output in outputs]
        if payloads[0] != payloads[1]:
            raise ValueError("Repeated wheel generation was not byte-for-byte deterministic")
        digest = hashlib.sha256(payloads[0]).hexdigest()
        args.digest.parent.mkdir(parents=True, exist_ok=True)
        args.digest.write_text(f"{digest}\n", encoding="ascii")
        print(f"Deterministic bundle SHA-256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
