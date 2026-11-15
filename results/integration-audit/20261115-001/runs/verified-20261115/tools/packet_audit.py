"""Compare saved JSON settings without inference or a comparability verdict.

Allow paths are exact dot-delimited key paths; allowing ``models`` does not allow
``models.target``. Arrays are compared as whole values. Added, removed, or replaced
objects are reported whole at their field path. No wildcard/subtree semantics.
Keys containing dots (or empty keys) are still reported using ``path_segments``;
they cannot be allowed through the dot-path CLI. No schema or default is assumed:
metadata absent in both inputs remains unknown, not verified equal.

Exit 0 means the report was written, even when unexplained changes exist. Exit 2
means invalid input/arguments or an output error. The output must be a new file.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys


_MISSING = object()


def _validate_json(value):
    """Validate dictionaries supplied directly, not only parsed JSON text."""
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("nonfinite numbers are not accepted")
        return
    if type(value) is list:
        for child in value:
            _validate_json(child)
        return
    if type(value) is dict:
        for key, child in value.items():
            if type(key) is not str:
                raise ValueError("JSON object keys must be strings")
            _validate_json(child)
        return
    raise ValueError("unsupported JSON value type: " + type(value).__name__)


def _equal(left, right):
    # Python otherwise equates True with 1, including inside arrays.
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(_equal(left[k], right[k]) for k in left)
    if type(left) is list:
        return len(left) == len(right) and all(_equal(a, b) for a, b in zip(left, right))
    return left == right


def _side(value):
    return {"present": False} if value is _MISSING else {"present": True, "value": value}


def compare_settings(left, right, allowed_paths=()):
    """Return every observed difference, classified by caller-declared allowance.

    Both roots must be JSON dictionaries. Comparison preserves JSON value types,
    so numeric 1 and 1.0 differ, as do boolean true and numeric 1. Key order does
    not matter; array order does. Nothing in this result establishes statistical
    comparability or the completeness of the supplied metadata.
    """
    for value in (left, right):
        if type(value) is not dict:
            raise ValueError("settings root must be a JSON object")
        _validate_json(value)
    paths = set()
    for path in allowed_paths:
        if not isinstance(path, str) or not path or any(not part for part in path.split(".")):
            raise ValueError("allow paths must contain nonempty dot-delimited key segments")
        paths.add(tuple(path.split(".")))
    changes = []

    def visit(a, b, segments):
        if type(a) is dict and type(b) is dict:
            for key in sorted(a.keys() | b.keys()):
                visit(a.get(key, _MISSING), b.get(key, _MISSING), segments + (key,))
        elif not _equal(a, b):
            changes.append({
                "path": ".".join(segments),
                "path_segments": list(segments),
                "left": _side(a),
                "right": _side(b),
                "classification": "allowed" if segments in paths else "unexplained",
            })

    visit(left, right, ())
    return {
        "allowed_paths": [".".join(path) for path in sorted(paths)],
        "allow_semantics": "exact",
        "changes": changes,
        "allowed_changes": [c for c in changes if c["classification"] == "allowed"],
        "unexplained_changes": [c for c in changes if c["classification"] == "unexplained"],
        "statistical_comparability": "not_assessed",
        "metadata_completeness": "unknown",
        "limitations": [
            "Allowed means caller-declared, not scientifically justified.",
            "Only supplied settings are compared; missing metadata is unknown.",
            "Arrays and added, removed, or replaced objects are reported whole.",
            "path_segments disambiguates literal dots and empty keys; these cannot be allowed by dot path.",
        ],
    }


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key: " + repr(key))
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("nonfinite JSON number: " + value)


def _read_settings(path):
    data = path.read_bytes()
    value = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object,
                       parse_constant=_reject_constant)
    return value, {"path": str(path.resolve()), "sha256": hashlib.sha256(data).hexdigest()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--left", required=True, type=Path)
    parser.add_argument("--right", required=True, type=Path)
    parser.add_argument("--allow", action="append", default=[], metavar="EXACT.DOT.PATH")
    parser.add_argument("--out", required=True, type=Path, help="New report file; never overwritten")
    args = parser.parse_args(argv)
    try:
        left, left_info = _read_settings(args.left)
        right, right_info = _read_settings(args.right)
        report = compare_settings(left, right, args.allow)
        tool = Path(__file__).resolve()
        report["inputs"] = {"left": left_info, "right": right_info}
        report["tool"] = {"path": str(tool), "sha256": hashlib.sha256(tool.read_bytes()).hexdigest()}
        text = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
        # Exclusive creation refuses existing files and symlinks, without a race
        # between an existence check and opening the output.
        with args.out.open("x", encoding="utf-8") as output:
            output.write(text)
    except (OSError, ValueError, RecursionError) as exc:
        parser.error(str(exc))
    print("Wrote %s: %d allowed, %d unexplained changes; comparability not assessed." % (
        args.out, len(report["allowed_changes"]), len(report["unexplained_changes"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
