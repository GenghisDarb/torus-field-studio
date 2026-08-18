from __future__ import annotations

import argparse
import functools
import http.server
import json
import os
import socketserver
import sys
import tempfile
import webbrowser
from pathlib import Path
from typing import Any

from .adapters.zenodo_tld_i import (
    extract_tld_i,
    fetch_tld_i,
    validate_release_source,
)
from .bundle import audit_bundle, compare_bundles, copy_field_json, export_field_csv
from .domains.beijing_pm25 import fetch_authoritative_source, materialize
from .kernels import LadderKernel
from .models import DomainPack, MatchedNullPolicy, RunSpec, canonical_json, validate_domain_pack
from .runs import AnalyticRun, LocalBrotRun
from .tld import (
    TLD_I_DOI,
    execute_modern_extension,
    export_historical_bundle_set,
    export_tld_bundle,
    reproduce_tld_i,
)
from .tld.heldout import authorize_scored_run, execute_scored_run
from .tld.heldout.adjudication import adjudicate, snapshot_result
from .tld.heldout.verification import verify_scored_run


def _print(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))


def _run_init(args: argparse.Namespace) -> int:
    target = Path(args.path).resolve()
    if target.exists() and any(target.iterdir()):
        raise ValueError(f"Refusing to initialize non-empty directory: {target}")
    target.mkdir(parents=True, exist_ok=True)
    (target / "domains").mkdir()
    (target / "results").mkdir()
    run_spec = {
        "schema_version": "1.0.0",
        "engine": "local_brot",
        "seed": 1407,
        "domain_id": "replace-me",
        "claim_level": "COMPUTED_DYNAMICAL",
        "grid": {"width": 56, "height": 40},
        "parameters": {"x_min": 0, "x_max": 1, "y_min": 0, "y_max": 1, "recovery_steps": 12},
        "classification_rules": {},
        "null_policy": {"kind": "preserve_multiset_shuffle", "count": 12, "seed": 1407},
    }
    (target / "run-spec.json").write_bytes(canonical_json(run_spec, pretty=True))
    (target / "README.md").write_text(
        "# TORUS study\n\nReplace the domain ID, add a domain pack, freeze, generate, and audit.\n",
        encoding="utf-8",
    )
    _print({"created": str(target), "next": "edit run-spec.json and add domains/domain.json"})
    return 0


def _run_validate(args: argparse.Namespace) -> int:
    path = Path(args.path)
    data = json.loads((path / "domain.json" if path.is_dir() else path).read_text(encoding="utf-8"))
    errors = validate_domain_pack(data)
    _print({"valid": not errors, "errors": errors, "path": str(path)})
    return 0 if not errors else 1


def _run_validate_tld_release(args: argparse.Namespace) -> int:
    receipt = validate_release_source(args.path)
    _print(receipt)
    return 0


def _run_freeze(args: argparse.Namespace) -> int:
    spec = RunSpec.from_file(args.path)
    target = Path(args.output) if args.output else Path(args.path).with_suffix(".frozen.json")
    payload = spec.to_dict() | {"specification_sha256": spec.sha256}
    target.write_bytes(canonical_json(payload, pretty=True))
    _print({"frozen": str(target), "sha256": spec.sha256})
    return 0


def _run_generate(args: argparse.Namespace) -> int:
    if args.kind == "analytic":
        result = AnalyticRun.from_file(args.spec).execute()
    else:
        if not args.domain:
            raise ValueError("--domain is required for local generation")
        domain = DomainPack.load(args.domain)
        result = LocalBrotRun.from_file(args.spec).execute(domain)
    target = result.export_tbx(args.output)
    audit = result.audit(target)
    _print(
        {
            "output": str(target),
            "run_id": result.run_id,
            "claim_level": result.claim_level.name,
            "statistics": result.statistics,
            "audit": audit.to_dict(),
        }
    )
    return 0 if audit.valid else 1


def _release_root(source: str | Path, quarantine: Path) -> Path:
    path = Path(source).resolve()
    if path.is_file():
        return extract_tld_i(path, quarantine)
    receipt = validate_release_source(path)
    return Path(str(receipt["release_root"]))


def _run_fetch_tld_release(args: argparse.Namespace) -> int:
    if args.doi != TLD_I_DOI:
        raise ValueError(f"Unsupported TLD release DOI: {args.doi}")
    target = Path(args.output)
    receipt = fetch_tld_i(target)
    _print(receipt | {"output": str(target)})
    return 0


def _run_fetch_heldout_source(args: argparse.Namespace) -> int:
    _print(fetch_authoritative_source(Path(args.output)))
    return 0


def _run_materialize_heldout(args: argparse.Namespace) -> int:
    receipt = materialize(Path(args.source), Path(args.study), Path(args.output))
    _print(receipt)
    return 0 if receipt["ready_for_scored_run_authorization"] else 1


def _run_authorize_heldout(args: argparse.Namespace) -> int:
    receipt = authorize_scored_run(
        Path(args.materialized),
        Path(args.study),
        Path(args.output),
        preregistration_commit=args.preregistration_commit,
        implementation_commit=args.implementation_commit,
    )
    _print(receipt)
    return 0


def _run_execute_heldout(args: argparse.Namespace) -> int:
    summary = execute_scored_run(Path(args.materialized), Path(args.study), Path(args.output))
    _print(summary)
    return 0


def _run_verify_heldout(args: argparse.Namespace) -> int:
    report = verify_scored_run(
        Path(args.materialized),
        Path(args.study),
        Path(args.scored),
        Path(args.output),
    )
    _print(report)
    return 0 if report["status"] == "verified" else 1


def _run_adjudicate_heldout(args: argparse.Namespace) -> int:
    result = adjudicate(Path(args.scored), Path(args.verification), Path(args.output))
    _print(result)
    return 0


def _run_snapshot_heldout(args: argparse.Namespace) -> int:
    result = snapshot_result(
        Path(args.scored),
        Path(args.verification),
        Path(args.adjudication),
        Path(args.output),
    )
    _print(result)
    return 0


def _run_reproduce_tld_i(args: argparse.Namespace) -> int:
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    quarantine = output / "source_quarantine"
    source_root = _release_root(args.source, quarantine)
    result = reproduce_tld_i(source_root)
    result_path = output / "tld_i_reproduction.json"
    result_path.write_bytes(canonical_json(result, pretty=True))
    modern = execute_modern_extension(source_root, result)
    modern_path = output / "modern_v21_compliance_extension.json"
    modern_path.write_bytes(canonical_json(modern, pretty=True))
    bundles = export_historical_bundle_set(result, output / "bundles")
    audits = {path.name: audit_bundle(path).to_dict() for path in bundles}
    _print(
        {
            "classification": "EXACT_REPRODUCTION",
            "high_level_outcome": "FIRST_PUBLISHED_TLD_RESULT_EXACTLY_REPRODUCED",
            "claim_level": "COMPUTED_DYNAMICAL",
            "tld_derived_status": "BLOCKED",
            "result": str(result_path),
            "modern_extension": str(modern_path),
            "bundles": [str(path) for path in bundles],
            "audits": audits,
        }
    )
    return 0 if all(receipt["valid"] for receipt in audits.values()) else 1


def _run_generate_tld(args: argparse.Namespace) -> int:
    specification = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    if specification.get("engine") != "tld":
        raise ValueError("TLD generation requires a run specification with engine=tld")
    if not args.domain:
        raise ValueError("--domain must identify the canonical archive or extracted release")
    profile = str(specification.get("parameters", {}).get("profile", "combined"))
    with tempfile.TemporaryDirectory(prefix="torusbrot-tld-source-") as temporary:
        source_root = _release_root(args.domain, Path(temporary) / "source")
        result = reproduce_tld_i(source_root)
    target = export_tld_bundle(result, profile, args.output)
    audit = audit_bundle(target)
    _print({"output": str(target), "profile": profile, "audit": audit.to_dict()})
    return 0 if audit.valid else 1


def _run_verify_tld_result(args: argparse.Namespace) -> int:
    report = audit_bundle(args.bundle)
    _print(
        {
            "verified": report.valid,
            "claim_ceiling": "COMPUTED_DYNAMICAL",
            "externally_validated": False,
            "audit": report.to_dict(),
        }
    )
    return 0 if report.valid else 1


def _run_nulls(args: argparse.Namespace) -> int:
    domain = DomainPack.load(args.domain)
    policy = MatchedNullPolicy(count=args.count, seed=args.seed)
    spec_data = {
        "schema_version": "1.0.0",
        "engine": "local_brot",
        "seed": args.seed,
        "domain_id": domain.domain_id,
        "claim_level": "COMPUTED_DYNAMICAL",
        "grid": {"width": 4, "height": 4},
        "parameters": {},
        "classification_rules": {},
        "null_policy": {"kind": policy.kind, "count": policy.count, "seed": policy.seed},
    }
    temporary = Path(os.environ.get("TEMP", ".")) / f"torusbrot-null-spec-{os.getpid()}.json"
    try:
        temporary.write_bytes(canonical_json(spec_data))
        kernel = LadderKernel(RunSpec.from_file(temporary), domain, policy)
        registry = kernel.null_registry()
    finally:
        temporary.unlink(missing_ok=True)
    if args.output:
        Path(args.output).write_bytes(canonical_json(registry, pretty=True))
    _print({"policy": policy.kind, "count": len(registry), "nulls": registry})
    return 0


def _run_audit(args: argparse.Namespace) -> int:
    report = audit_bundle(args.bundle)
    _print(report.to_dict())
    return 0 if report.valid else 1


def _run_compare(args: argparse.Namespace) -> int:
    _print(compare_bundles(args.left, args.right))
    return 0


def _run_export(args: argparse.Namespace) -> int:
    target = Path(args.output)
    if args.format == "csv":
        export_field_csv(args.bundle, target)
    else:
        copy_field_json(args.bundle, target)
    _print({"format": args.format, "output": str(target)})
    return 0


def _find_studio() -> Path:
    here = Path(__file__).resolve()
    candidates = [parent / "apps" / "studio" / "dist" for parent in here.parents]
    for candidate in candidates:
        if (candidate / "index.html").exists():
            return candidate
    raise ValueError(
        "Studio build not found. Run `pnpm install && pnpm run build` in the repository."
    )


def _run_studio(args: argparse.Namespace) -> int:
    studio = _find_studio()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(studio))
    with socketserver.TCPServer((args.host, args.port), handler) as server:
        url = f"http://{args.host}:{args.port}"
        print(f"TORUS Field Studio serving at {url}. Press Ctrl+C to stop.")
        if not args.no_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStudio stopped.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="torusbrot", description="TORUS Field Studio CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="create a study directory")
    init.add_argument("path")
    init.set_defaults(handler=_run_init)

    validate = subparsers.add_parser("validate", help="validate an input contract")
    validate_sub = validate.add_subparsers(dest="kind", required=True)
    domain = validate_sub.add_parser("domain-pack")
    domain.add_argument("path")
    domain.set_defaults(handler=_run_validate)
    tld_release = validate_sub.add_parser("tld-release")
    tld_release.add_argument("path")
    tld_release.set_defaults(handler=_run_validate_tld_release)

    fetch = subparsers.add_parser("fetch", help="fetch a registered public source release")
    fetch_sub = fetch.add_subparsers(dest="kind", required=True)
    tld_fetch = fetch_sub.add_parser("tld-release")
    tld_fetch.add_argument("--doi", default=TLD_I_DOI)
    tld_fetch.add_argument("--output", "-o", required=True)
    tld_fetch.set_defaults(handler=_run_fetch_tld_release)
    heldout_fetch = fetch_sub.add_parser("heldout-source")
    heldout_fetch.add_argument("--output", "-o", required=True)
    heldout_fetch.set_defaults(handler=_run_fetch_heldout_source)

    materialize_parser = subparsers.add_parser(
        "materialize", help="materialize a registered study before metrics"
    )
    materialize_sub = materialize_parser.add_subparsers(dest="materialize_kind", required=True)
    heldout_materialize = materialize_sub.add_parser("heldout-study")
    heldout_materialize.add_argument("--source", required=True)
    heldout_materialize.add_argument("--study", required=True)
    heldout_materialize.add_argument("--output", "-o", required=True)
    heldout_materialize.set_defaults(handler=_run_materialize_heldout)

    authorize = subparsers.add_parser("authorize", help="freeze a scored-run identity")
    authorize_sub = authorize.add_subparsers(dest="authorize_kind", required=True)
    heldout_authorize = authorize_sub.add_parser("heldout-study")
    heldout_authorize.add_argument("--materialized", required=True)
    heldout_authorize.add_argument("--study", required=True)
    heldout_authorize.add_argument("--output", "-o", required=True)
    heldout_authorize.add_argument("--preregistration-commit", required=True)
    heldout_authorize.add_argument("--implementation-commit", required=True)
    heldout_authorize.set_defaults(handler=_run_authorize_heldout)

    execute = subparsers.add_parser("execute", help="execute an authorized scored study")
    execute_sub = execute.add_subparsers(dest="execute_kind", required=True)
    heldout_execute = execute_sub.add_parser("heldout-study")
    heldout_execute.add_argument("--materialized", required=True)
    heldout_execute.add_argument("--study", required=True)
    heldout_execute.add_argument("--output", "-o", required=True)
    heldout_execute.set_defaults(handler=_run_execute_heldout)

    adjudicate_parser = subparsers.add_parser("adjudicate", help="adjudicate a verified study")
    adjudicate_sub = adjudicate_parser.add_subparsers(dest="adjudicate_kind", required=True)
    heldout_adjudicate = adjudicate_sub.add_parser("heldout-study")
    heldout_adjudicate.add_argument("--scored", required=True)
    heldout_adjudicate.add_argument("--verification", required=True)
    heldout_adjudicate.add_argument("--output", "-o", required=True)
    heldout_adjudicate.set_defaults(handler=_run_adjudicate_heldout)

    snapshot = subparsers.add_parser("snapshot", help="create a tracked result snapshot")
    snapshot_sub = snapshot.add_subparsers(dest="snapshot_kind", required=True)
    heldout_snapshot = snapshot_sub.add_parser("heldout-study")
    heldout_snapshot.add_argument("--scored", required=True)
    heldout_snapshot.add_argument("--verification", required=True)
    heldout_snapshot.add_argument("--adjudication", required=True)
    heldout_snapshot.add_argument("--output", "-o", required=True)
    heldout_snapshot.set_defaults(handler=_run_snapshot_heldout)

    freeze = subparsers.add_parser("freeze", help="canonicalize and hash a run specification")
    freeze.add_argument("path")
    freeze.add_argument("--output", "-o")
    freeze.set_defaults(handler=_run_freeze)

    generate = subparsers.add_parser("generate", help="generate a field bundle")
    generate_sub = generate.add_subparsers(dest="kind", required=True)
    for name in ("analytic", "local", "tld"):
        child = generate_sub.add_parser(name)
        child.add_argument("--spec", required=True)
        child.add_argument("--domain")
        child.add_argument("--output", "-o", required=True)
        child.set_defaults(handler=_run_generate_tld if name == "tld" else _run_generate)

    reproduce = subparsers.add_parser("reproduce", help="reproduce a registered result")
    reproduce_sub = reproduce.add_subparsers(dest="kind", required=True)
    tld_i = reproduce_sub.add_parser("tld-i")
    tld_i.add_argument("--source", required=True)
    tld_i.add_argument("--output", "-o", required=True)
    tld_i.set_defaults(handler=_run_reproduce_tld_i)

    verify = subparsers.add_parser("verify", help="independently verify a result bundle")
    verify_sub = verify.add_subparsers(dest="kind", required=True)
    tld_result = verify_sub.add_parser("tld-result")
    tld_result.add_argument("bundle")
    tld_result.set_defaults(handler=_run_verify_tld_result)
    heldout_result = verify_sub.add_parser("heldout-study")
    heldout_result.add_argument("--materialized", required=True)
    heldout_result.add_argument("--study", required=True)
    heldout_result.add_argument("--scored", required=True)
    heldout_result.add_argument("--output", "-o", required=True)
    heldout_result.set_defaults(handler=_run_verify_heldout)

    nulls = subparsers.add_parser("nulls", help="matched-null operations")
    null_sub = nulls.add_subparsers(dest="null_command", required=True)
    null_generate = null_sub.add_parser("generate")
    null_generate.add_argument("--domain", required=True)
    null_generate.add_argument("--count", type=int, default=12)
    null_generate.add_argument("--seed", type=int, default=1407)
    null_generate.add_argument("--output", "-o")
    null_generate.set_defaults(handler=_run_nulls)

    audit = subparsers.add_parser("audit", help="verify a TBX bundle")
    audit.add_argument("bundle")
    audit.set_defaults(handler=_run_audit)

    compare = subparsers.add_parser("compare", help="compare two TBX bundles")
    compare.add_argument("left")
    compare.add_argument("right")
    compare.set_defaults(handler=_run_compare)

    export = subparsers.add_parser("export", help="export a field table")
    export.add_argument("bundle")
    export.add_argument("--format", choices=("csv", "json"), required=True)
    export.add_argument("--output", "-o", required=True)
    export.set_defaults(handler=_run_export)

    studio = subparsers.add_parser("studio", help="serve the built browser studio")
    studio.add_argument("--host", default="127.0.0.1")
    studio.add_argument("--port", type=int, default=4173)
    studio.add_argument("--no-browser", action="store_true")
    studio.set_defaults(handler=_run_studio)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
