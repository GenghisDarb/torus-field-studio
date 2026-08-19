"""Generate lightweight Python TypedDict bindings from authoritative JSON Schemas."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
SCHEMA_ROOT = ROOT / "schemas"
OUTPUT = ROOT / "python" / "torusbrot" / "tld" / "generated_types.py"
PREFIXES = (
    "boundary-condition",
    "coordinate-system",
    "effective-parent-audit",
    "field-component",
    "field-observation",
    "geometric-scale-registry",
    "geometry-",
    "independent-verification",
    "mask-contract",
    "nested-replicate-registry",
    "operation-depth-registry",
    "parent-registry",
    "projection-registry",
    "representation-agreement",
    "scout-eligibility",
    "structure-channel-registry",
    "tld-",
)


def class_name(title: str) -> str:
    return "".join(part.capitalize() for part in re.split(r"[^A-Za-z0-9]+", title) if part)


def annotation(schema: dict[str, Any]) -> str:
    if "const" in schema:
        return f"Literal[{schema['const']!r}]"
    if "enum" in schema:
        return "Literal[" + ", ".join(repr(value) for value in schema["enum"]) + "]"
    kind = schema.get("type")
    if isinstance(kind, list):
        values = [annotation({"type": value}) for value in kind]
        return " | ".join("None" if value == "None" else value for value in values)
    if kind == "string":
        return "str"
    if kind == "integer":
        return "int"
    if kind == "number":
        return "float"
    if kind == "boolean":
        return "bool"
    if kind == "null":
        return "None"
    if kind == "array":
        return f"list[{annotation(schema.get('items', {}))}]"
    if kind == "object":
        return "dict[str, Any]"
    return "Any"


def main() -> None:
    schemas = []
    for path in sorted(SCHEMA_ROOT.rglob("*.schema.json")):
        relative = path.relative_to(SCHEMA_ROOT).as_posix()
        if not relative.startswith(PREFIXES):
            continue
        schemas.append((relative, json.loads(path.read_text(encoding="utf-8"))))
    uses_optional = any(
        set(schema.get("properties", {})) - set(schema.get("required", [])) for _, schema in schemas
    )
    typing_imports = "Any, Literal, Required, TypedDict"
    if uses_optional:
        typing_imports = "Any, Literal, NotRequired, Required, TypedDict"
    lines = [
        '"""Generated from canonical JSON Schemas. Do not edit by hand."""',
        "",
        "from __future__ import annotations",
        "",
        f"from typing import {typing_imports}",
        "",
        "SCHEMA_IDS = {",
    ]
    for relative, schema in schemas:
        lines.append(f"    {relative!r}: {schema['$id']!r},")
    lines.extend(["}", ""])
    for _, schema in schemas:
        name = class_name(schema["title"])
        required = set(schema.get("required", []))
        lines.append(f"class {name}(TypedDict, total=False):")
        properties = schema.get("properties", {})
        if not properties:
            lines.append("    pass")
        for field, field_schema in properties.items():
            wrapper = "Required" if field in required else "NotRequired"
            lines.append(f"    {field}: {wrapper}[{annotation(field_schema)}]")
        lines.append("")
    content = "\n".join(lines).rstrip() + "\n"
    formatted = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--stdin-filename", str(OUTPUT), "-"],
        input=content,
        text=True,
        capture_output=True,
        check=False,
    )
    if formatted.returncode:
        raise SystemExit(formatted.stderr)
    content = formatted.stdout
    if "--check" in __import__("sys").argv:
        existing = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if existing != content:
            raise SystemExit(f"Generated Python schema types are stale: {OUTPUT.relative_to(ROOT)}")
        print("Generated Python schema types are current.")
    else:
        OUTPUT.write_text(content, encoding="utf-8")
        print(f"Generated {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
