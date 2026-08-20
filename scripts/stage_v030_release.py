from __future__ import annotations

import argparse
import hashlib
import shutil
import zipfile
from pathlib import Path

from release_manifest import build_manifest

ROOT = Path(__file__).resolve().parents[1]
RECOVERY = ROOT / "studies" / "v0.3.0-recovery"


def files_under(root: Path, prefix: str) -> dict[str, Path]:
    return {
        (
            f"{prefix}/{path.relative_to(root).as_posix()}"
            if prefix
            else path.relative_to(root).as_posix()
        ): path
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def deterministic_zip(target: Path, members: dict[str, Path]) -> None:
    payloads = {name: path.read_bytes() for name, path in sorted(members.items())}
    sums = "".join(
        f"{hashlib.sha256(payload).hexdigest()}  {name}\n" for name, payload in payloads.items()
    ).encode()
    payloads["PACKAGE_SHA256SUMS.txt"] = sums
    with zipfile.ZipFile(
        target,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for name, payload in sorted(payloads.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payload)


def require_empty(directory: Path) -> None:
    if directory.exists() and any(directory.iterdir()):
        raise SystemExit(f"release staging directory must be empty: {directory}")
    directory.mkdir(parents=True, exist_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage the complete v0.3.0 release")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--sbom", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    require_empty(output)

    distributions = sorted(args.dist.resolve().glob("torusbrot-0.3.0*"))
    if len(distributions) != 2:
        raise SystemExit("expected one v0.3.0 wheel and one source distribution")
    for path in distributions:
        shutil.copyfile(path, output / path.name)

    direct_assets = {
        ROOT / "docs/geometry_method_v2.md": "geometry-method-v2-specification.md",
        RECOVERY / "publication/technical-report.md": "v0.3.0-technical-report.md",
        RECOVERY / "publication/plain-language-report.md": "v0.3.0-plain-language-report.md",
        RECOVERY / "wind_pilot/wind_farm_pilot.tbx.zip": "wind-farm-pilot-v0.3.0.tbx.zip",
        RECOVERY / "tbx/method-calibration-v2.tbx.zip": "method-calibration-v2.tbx.zip",
        RECOVERY
        / "tbx/representation-equivariance-v2.tbx.zip": "representation-equivariance-v2.tbx.zip",
        RECOVERY
        / "tbx/heldout-fluidic-pinball-v0.3.0.tbx.zip": "heldout-fluidic-pinball-v0.3.0.tbx.zip",
        RECOVERY / "tbx/geometry-method-v2-combined-v0.3.0.tbx.zip": (
            "geometry-method-v2-combined-v0.3.0.tbx.zip"
        ),
        args.sbom.resolve(): "sbom-v0.3.0.spdx.json",
    }
    for source, name in direct_assets.items():
        if not source.is_file():
            raise SystemExit(f"release asset missing: {source}")
        shutil.copyfile(source, output / name)

    calibration_members: dict[str, Path] = {}
    for directory in ("calibration", "bridge", "freeze", "geometry", "statistics", "verification"):
        calibration_members.update(files_under(RECOVERY / directory, directory))
    calibration_members["docs/geometry_method_v2.md"] = ROOT / "docs/geometry_method_v2.md"
    deterministic_zip(output / "method-v2-calibration-v0.3.0.zip", calibration_members)

    deterministic_zip(
        output / "wind-farm-engineering-pilot-v0.3.0.zip",
        files_under(RECOVERY / "wind_pilot", "wind_pilot"),
    )

    replication_members = files_under(ROOT / "replication/v0.3.0", "")
    replication_members.update(files_under(RECOVERY / "heldout", "heldout"))
    replication_members.update(files_under(RECOVERY / "candidate_selection", "candidate_selection"))
    replication_members.update(files_under(RECOVERY / "tbx", "tbx"))
    replication_members["tbx/wind_farm_pilot.tbx.zip"] = (
        RECOVERY / "wind_pilot/wind_farm_pilot.tbx.zip"
    )
    replication_members["docs/geometry_method_v2.md"] = ROOT / "docs/geometry_method_v2.md"
    for name in (
        "build_v030_geometry_tbx.py",
        "materialize_v030_pinball_source.py",
        "verify_v030_pinball_heldout.py",
        "verify_v030_pinball_raw.py",
    ):
        replication_members[f"scripts/{name}"] = ROOT / "scripts" / name
    deterministic_zip(output / "v0.3.0-replication-package.zip", replication_members)

    deterministic_zip(
        output / "controllergate-read-only-transfer-v0.3.0.zip",
        files_under(
            ROOT / "replication/controllergate-transfer-v0.3.0",
            "controllergate-transfer-v0.3.0",
        ),
    )
    manifest = build_manifest(output, "v0.3.0", args.commit)
    print(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
