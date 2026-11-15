"""Single registration hook. Candidate owners supply functions, never edit this map.

Builder signature: (documents, config, extractor) -> {content: JSON, status?: str}.
Builders receive only an evaluator-approved exact source set. Registration pins
the builder's module bytes and prompt, not merely a backend name.
"""
import inspect
from dataclasses import dataclass
from pathlib import Path

from .contracts import sha256_text, sha256_bytes


@dataclass(frozen=True)
class Builder:
    method_id: str
    function: object
    prompt_version: str
    prompt_sha256: str
    implementation_hash: str
    allows_empty: bool = False


_BUILDERS = {}


def register_builder(method_id, function, *, prompt_version, prompt_sha256, allows_empty=False):
    if not method_id or not callable(function) or not prompt_version:
        raise ValueError("method, callable and prompt version are required")
    if len(prompt_sha256) != 64 or any(c not in "0123456789abcdef" for c in prompt_sha256):
        raise ValueError("prompt_sha256 must be a SHA256")
    source = inspect.getsourcefile(function)
    implementation = sha256_bytes(Path(source).read_bytes()) if source else sha256_text(inspect.getsource(function))
    builder = Builder(method_id, function, prompt_version, prompt_sha256, implementation, bool(allows_empty))
    old = _BUILDERS.get(method_id)
    if old is not None and old != builder:
        raise ValueError("method already registered with different implementation")
    _BUILDERS[method_id] = builder
    return builder


def get_builder(method_id):
    if method_id not in _BUILDERS:
        raise ValueError("unregistered profile method: " + str(method_id))
    return _BUILDERS[method_id]


def registered_methods():
    return tuple(sorted(_BUILDERS))
