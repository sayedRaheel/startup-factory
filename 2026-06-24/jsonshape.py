#!/usr/bin/env python3
"""jsonshape - print the *shape* (schema skeleton) of a JSON document.

Drop a giant, unfamiliar API response in and get back a compact tree of its
keys, types, array lengths and nesting depth -- without dumping the whole
thing or hand-rolling a jq expression.

Standard library only. No third-party dependencies.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, Optional

__version__ = "1.0.0"

# Tree-drawing glyphs.
TEE = "├─ "
ELBOW = "└─ "
PIPE = "│  "
SPACE = "   "

SCALARS = ("str", "int", "float", "bool", "null")


# --------------------------------------------------------------------------
# Schema inference
# --------------------------------------------------------------------------
def schema_of(value: Any) -> Dict[str, Any]:
    """Infer a schema node from a single decoded JSON value."""
    if value is None:
        return {"k": "null"}
    if isinstance(value, bool):  # bool before int -- bool is a subclass of int
        return {"k": "bool", "sample": value}
    if isinstance(value, int):
        return {"k": "int", "sample": value}
    if isinstance(value, float):
        return {"k": "float", "sample": value}
    if isinstance(value, str):
        return {"k": "str", "sample": value}
    if isinstance(value, list):
        elem: Optional[Dict[str, Any]] = None
        for item in value:
            s = schema_of(item)
            elem = s if elem is None else merge(elem, s)
        return {"k": "array", "lmin": len(value), "lmax": len(value), "elem": elem}
    if isinstance(value, dict):
        fields: Dict[str, Dict[str, Any]] = {}
        for key, val in value.items():
            fields[key] = {"schema": schema_of(val), "present": 1}
        return {"k": "object", "fields": fields, "samples": 1}
    # Fallback for anything json somehow produced that we did not expect.
    return {"k": type(value).__name__}


def merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two schema nodes describing values seen in the same position."""
    if a["k"] == b["k"]:
        if a["k"] == "object":
            samples = a["samples"] + b["samples"]
            fields = dict(a["fields"])
            for key, info in b["fields"].items():
                if key in fields:
                    fields[key] = {
                        "schema": merge(fields[key]["schema"], info["schema"]),
                        "present": fields[key]["present"] + info["present"],
                    }
                else:
                    fields[key] = dict(info)
            return {"k": "object", "fields": fields, "samples": samples}
        if a["k"] == "array":
            elem = a["elem"]
            if b["elem"] is not None:
                elem = b["elem"] if elem is None else merge(elem, b["elem"])
            return {
                "k": "array",
                "lmin": min(a["lmin"], b["lmin"]),
                "lmax": max(a["lmax"], b["lmax"]),
                "elem": elem,
            }
        # Two scalars of the same kind: keep the first sample.
        return a

    # Different kinds -> a union of type names.
    types = set()
    for node in (a, b):
        if node["k"] == "union":
            types |= node["types"]
        else:
            types.add(node["k"])
    return {"k": "union", "types": types}


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------
def type_label(node: Dict[str, Any]) -> str:
    k = node["k"]
    if k in SCALARS:
        return k
    if k == "union":
        return "|".join(sorted(node["types"]))
    if k == "array":
        if node["lmin"] == node["lmax"]:
            length = str(node["lmin"])
        else:
            length = f"{node['lmin']}..{node['lmax']}"
        label = f"array[{length}]"
        elem = node["elem"]
        if elem is None:
            return label + " (empty)"
        if elem["k"] in SCALARS or elem["k"] == "union":
            return f"{label} of {type_label(elem)}"
        return f"{label} of {type_label(elem)}"
    if k == "object":
        return f"object{{{len(node['fields'])}}}"
    return k


def terminal_element(node: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Follow nested arrays down to the first non-array element schema."""
    while node is not None and node["k"] == "array":
        node = node["elem"]
    return node


def has_children(node: Dict[str, Any]) -> bool:
    if node["k"] == "object":
        return bool(node["fields"])
    if node["k"] == "array":
        term = terminal_element(node["elem"]) if node["elem"] else None
        return term is not None and term["k"] == "object"
    return False


def render(node, name, prefix, is_last, lines, depth, maxdepth, show_samples):
    """Append rendered tree lines for ``node`` to ``lines``."""
    connector = "" if name is None else (ELBOW if is_last else TEE)
    label = type_label(node)

    annotation = ""
    if name is not None and "_optional" in node:
        present, total = node["_optional"]
        if present < total:
            annotation = f"  ({present}/{total})"

    sample = ""
    if show_samples and node["k"] in ("str", "int", "float", "bool") and "sample" in node:
        sample = f"  = {json.dumps(node['sample'])}"

    field_part = "" if name is None else f"{name}: "
    lines.append(f"{prefix}{connector}{field_part}{label}{annotation}{sample}")

    if maxdepth is not None and depth >= maxdepth:
        if has_children(node):
            child_prefix = prefix + ("" if name is None else (SPACE if is_last else PIPE))
            lines.append(f"{child_prefix}{ELBOW}…")
        return

    child_prefix = prefix + ("" if name is None else (SPACE if is_last else PIPE))

    if node["k"] == "object":
        items = list(node["fields"].items())
        for i, (key, info) in enumerate(items):
            child = dict(info["schema"])
            child["_optional"] = (info["present"], node["samples"])
            display = key if info["present"] >= node["samples"] else key + "?"
            render(child, display, child_prefix, i == len(items) - 1,
                   lines, depth + 1, maxdepth, show_samples)
    elif node["k"] == "array":
        # type_label already prints the full "of array[..] of object{N}" chain
        # inline, so we only need to expand fields when the chain ends in an
        # object. Scalar/union element types need no further lines.
        term = terminal_element(node["elem"]) if node["elem"] else None
        if term is not None and term["k"] == "object":
            items = list(term["fields"].items())
            for i, (key, info) in enumerate(items):
                child = dict(info["schema"])
                child["_optional"] = (info["present"], term["samples"])
                display = key if info["present"] >= term["samples"] else key + "?"
                render(child, display, child_prefix, i == len(items) - 1,
                       lines, depth + 1, maxdepth, show_samples)


# --------------------------------------------------------------------------
# Input handling
# --------------------------------------------------------------------------
def load_value(text: str, ndjson: bool) -> Any:
    """Return a single schema-able value (NDJSON merges every line)."""
    if ndjson:
        merged: Optional[Dict[str, Any]] = None
        count = 0
        for line_no, line in enumerate(text.splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON on line {line_no}: {exc}") from exc
            s = schema_of(obj)
            merged = s if merged is None else merge(merged, s)
            count += 1
        if merged is None:
            raise ValueError("no JSON records found in NDJSON input")
        return merged, count
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc


def read_input(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        raise ValueError(f"no such file: {path}")
    except OSError as exc:
        raise ValueError(f"cannot read {path}: {exc}")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="jsonshape",
        description="Print the shape (schema skeleton) of a JSON document.",
        epilog="Examples:\n"
               "  jsonshape data.json\n"
               "  curl -s api/users | jsonshape -\n"
               "  jsonshape --ndjson events.log\n"
               "  jsonshape --depth 2 --samples big.json\n"
               "  jsonshape --json data.json > schema.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("file", nargs="?", default="-",
                   help="JSON file to inspect (default: stdin, or '-')")
    p.add_argument("--ndjson", action="store_true",
                   help="treat input as newline-delimited JSON and merge records")
    p.add_argument("--depth", type=int, metavar="N",
                   help="limit output to N levels of nesting")
    p.add_argument("--samples", action="store_true",
                   help="show an example value beside each scalar leaf")
    p.add_argument("--json", action="store_true", dest="as_json",
                   help="emit the inferred schema as JSON instead of a tree")
    p.add_argument("--version", action="version",
                   version=f"%(prog)s {__version__}")
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.depth is not None and args.depth < 0:
        parser.error("--depth must be >= 0")

    try:
        text = read_input(args.file)
        if not text.strip():
            raise ValueError("input is empty")
        loaded = load_value(text, args.ndjson)
    except ValueError as exc:
        print(f"jsonshape: error: {exc}", file=sys.stderr)
        return 1

    ndjson_count = None
    if args.ndjson:
        node, ndjson_count = loaded
    else:
        node = schema_of(loaded)

    if args.as_json:
        json.dump(node, sys.stdout, indent=2, default=lambda o: sorted(o)
                  if isinstance(o, set) else str(o))
        sys.stdout.write("\n")
        return 0

    if args.ndjson:
        print(f"# merged {ndjson_count} NDJSON record(s)")

    lines: list = []
    render(node, None, "", True, lines, 0, args.depth, args.samples)
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(130)
