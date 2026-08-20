# ruff: noqa: E501 -- deposited names and custody language are retained verbatim.
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

import h5py

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE = ROOT / "external_cache" / "v0.3.0-field-20794709" / "ExperimentalDataset.full.zip"
DEFAULT_EXTRACTED = ROOT / "external_cache" / "v0.3.0-field-20794709" / "extracted"
DEFAULT_OUT = ROOT / "studies" / "v0.3.0-recovery" / "heldout" / "materialization"
PUBLISHED_SIZE = 1333197134
PUBLISHED_MD5 = "6629a8e110b1682b9361de37d8be4afb"
SELECTION_COMMIT = "590f6ea5896d3813c3a0a673e108381a4e3d87da"
H5_PATTERN = re.compile(r"^ExperimentalDataset/Case_p_(.+)\.h5$")


def canonical(value: Any, *, pretty: bool = False) -> bytes:
    options: dict[str, Any] = {"sort_keys": True, "ensure_ascii": False, "allow_nan": False}
    options.update(indent=2 if pretty else None, separators=None if pretty else (",", ":"))
    return (json.dumps(value, **options) + "\n").encode()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value, pretty=True))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(canonical(row) for row in rows))


def hash_file(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        while block := handle.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def safe_member(info: zipfile.ZipInfo) -> bool:
    name = info.filename
    path = PurePosixPath(name)
    return bool(
        name
        and "\\" not in name
        and "\x00" not in name
        and not path.is_absolute()
        and all(part not in {"", ".", ".."} for part in path.parts)
        and not (len(path.parts[0]) >= 2 and path.parts[0][1] == ":")
    )


def attr_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, int | float | str | bool) or value is None:
        return value
    return str(value)


def parse_p(name: str) -> float:
    token = name.removeprefix("ExperimentalDataset/Case_p_").removesuffix(".h5")
    token = token.removesuffix("_zero").removesuffix("_upward")
    return float(token.replace("m", "-").replace("p", "."))


def main() -> None:
    parser = argparse.ArgumentParser(description="Materialize the frozen fluidic-pinball source without field metrics")
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--extracted", type=Path, default=DEFAULT_EXTRACTED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    archive_path = args.archive.resolve()
    extracted = args.extracted.resolve()
    out = args.output.resolve()
    if archive_path.stat().st_size != PUBLISHED_SIZE:
        raise SystemExit("PINBALL_SOURCE_SIZE_MISMATCH")
    md5 = hash_file(archive_path, "md5")
    if md5 != PUBLISHED_MD5:
        raise SystemExit("PINBALL_SOURCE_MD5_MISMATCH")
    sha256 = hash_file(archive_path, "sha256")
    out.mkdir(parents=True, exist_ok=True)
    extracted.mkdir(parents=True, exist_ok=True)
    inventory: list[dict[str, Any]] = []
    structures: list[dict[str, Any]] = []
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        if len(infos) != 59 or any(not safe_member(info) for info in infos):
            raise SystemExit("PINBALL_ARCHIVE_INVENTORY_UNSAFE_OR_CHANGED")
        h5_infos = [info for info in infos if H5_PATTERN.fullmatch(info.filename)]
        if len(h5_infos) != 57:
            raise SystemExit("PINBALL_HDF5_ACQUISITION_COUNT_MISMATCH")
        for info in infos:
            inventory.append(
                {
                    "path": info.filename,
                    "is_directory": info.is_dir(),
                    "uncompressed_size": info.file_size,
                    "compressed_size": info.compress_size,
                    "compression_method": info.compress_type,
                    "crc32": f"{info.CRC:08x}",
                }
            )
        for info in h5_infos:
            target = extracted.joinpath(*PurePosixPath(info.filename).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists() or target.stat().st_size != info.file_size:
                with archive.open(info) as source, target.open("wb") as destination:
                    shutil.copyfileobj(source, destination, length=8 * 1024 * 1024)
            with h5py.File(target, "r") as source:
                datasets = {
                    name: {
                        "shape": list(source[name].shape),
                        "dtype": str(source[name].dtype),
                        "chunks": None if source[name].chunks is None else list(source[name].chunks),
                        "compression": source[name].compression,
                    }
                    for name in sorted(source)
                    if isinstance(source[name], h5py.Dataset)
                }
                if set(datasets) != {"U", "V", "X", "Y"}:
                    raise SystemExit(f"PINBALL_HDF5_DATASET_CONTRACT_MISMATCH:{info.filename}")
                if datasets["U"]["shape"] != datasets["V"]["shape"]:
                    raise SystemExit(f"PINBALL_VECTOR_COMPONENT_SHAPE_MISMATCH:{info.filename}")
                if (
                    datasets["X"]["shape"] != datasets["Y"]["shape"]
                    or len(datasets["U"]["shape"]) != 3
                    or datasets["U"]["shape"][1:] != datasets["X"]["shape"]
                ):
                    raise SystemExit(f"PINBALL_COORDINATE_SHAPE_MISMATCH:{info.filename}")
                attributes = {name: attr_value(value) for name, value in sorted(source.attrs.items())}
                structures.append(
                    {
                        "member": info.filename,
                        "extracted_size": target.stat().st_size,
                        "p_from_filename": parse_p(info.filename),
                        "role": "UNACTUATED_REFERENCE" if info.filename.endswith("_zero.h5") else "ACTUATED_OR_PRIMARY",
                        "snapshot_axis": 0,
                        "spatial_axes": [1, 2],
                        "datasets": datasets,
                        "attributes": attributes,
                        "field_values_read": False,
                    }
                )
    inventory_bytes = b"".join(canonical(row) for row in inventory)
    archive_inventory_sha256 = hashlib.sha256(inventory_bytes).hexdigest()
    primary = sorted(
        (
            row["member"]
            for row in structures
            if row["role"] == "ACTUATED_OR_PRIMARY" and not row["member"].endswith("_upward.h5")
        ),
        key=parse_p,
    )
    references = {row["member"] for row in structures if row["role"] == "UNACTUATED_REFERENCE"}
    structure_by_member = {row["member"]: row for row in structures}
    pairs = []
    for index, member in enumerate(primary):
        reference = member.removesuffix(".h5") + "_zero.h5"
        if reference not in references:
            raise SystemExit(f"PINBALL_PAIRED_REFERENCE_MISSING:{member}")
        actuated_structure = structure_by_member[member]
        reference_structure = structure_by_member[reference]
        for dataset_name in ("U", "V", "X", "Y"):
            actuated_dataset = actuated_structure["datasets"][dataset_name]
            reference_dataset = reference_structure["datasets"][dataset_name]
            if actuated_dataset["dtype"] != reference_dataset["dtype"]:
                raise SystemExit(f"PINBALL_PAIRED_DATASET_DTYPE_MISMATCH:{member}:{dataset_name}")
        actuated_grid_shape = actuated_structure["datasets"]["X"]["shape"]
        reference_grid_shape = reference_structure["datasets"]["X"]["shape"]
        pairs.append(
            {
                "pair_id": f"PAIR_{index + 1:02d}",
                "actuated_member": member,
                "reference_member": reference,
                "p": parse_p(member),
                "statistical_unit": "PAIRED_ACQUISITION_BLOCK",
                "reference_acquired_immediately_before_actuated": True,
                "reference_reused": False,
                "actuated_snapshot_count": actuated_structure["datasets"]["U"]["shape"][0],
                "reference_snapshot_count": reference_structure["datasets"]["U"]["shape"][0],
                "actuated_grid_shape": actuated_grid_shape,
                "reference_grid_shape": reference_grid_shape,
                "spatial_grid_shape_match": actuated_grid_shape == reference_grid_shape,
                "pairwise_cell_alignment": "FORBIDDEN_COMPARE_ACQUISITION_LEVEL_CHANNELS_ONLY",
                "campaign_cluster": "DEPOSIT_LEVEL_SINGLE_SYSTEM_CLUSTER",
                "population_independent_system": False,
            }
        )
    if len(pairs) != 28 or len({row["reference_member"] for row in pairs}) != 28:
        raise SystemExit("PINBALL_PAIRING_CONTRACT_MISMATCH")
    write_jsonl(out / "archive_inventory.jsonl", inventory)
    write_jsonl(out / "hdf5_structure_registry.jsonl", structures)
    write_jsonl(out / "paired_acquisition_registry.jsonl", pairs)
    write_json(
        out / "source_custody.json",
        {
            "schema_version": "1.0.0",
            "status": "PASS",
            "candidate_id": "actuated_fluidic_pinball_piv",
            "doi": "10.5281/zenodo.20794709",
            "license": "CC-BY-4.0",
            "selection_commit": SELECTION_COMMIT,
            "archive_name": "ExperimentalDataset.zip",
            "published_size_bytes": PUBLISHED_SIZE,
            "published_md5": PUBLISHED_MD5,
            "verified_md5": md5,
            "verified_sha256": sha256,
            "archive_inventory_sha256": archive_inventory_sha256,
            "archive_safe": True,
            "entry_count": len(inventory),
            "hdf5_acquisition_count": len(structures),
            "paired_block_count": len(pairs),
            "raw_field_values_read": False,
            "field_statistics_computed": False,
            "candidate_substitution": False,
        },
    )
    write_json(
        out / "source_materialization_receipt.json",
        {
            "status": "PASS_STRUCTURE_ONLY",
            "source_hash_verified": True,
            "archive_inventory_exact": True,
            "hdf5_headers_inspected": True,
            "hdf5_values_read": False,
            "paired_acquisition_count": 28,
            "unpaired_upward_auxiliary_count": 1,
            "preregistration_authorized": True,
            "scored_execution_authorized": False,
        },
    )
    print(json.dumps({"status": "PASS_STRUCTURE_ONLY", "sha256": sha256, "pairs": len(pairs), "structures": len(structures)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
