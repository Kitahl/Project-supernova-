#!/usr/bin/env python3
"""Strict JSON boundary for Supernova authority and evidence inputs.

Python's stdlib JSON decoder/encoder accepts non-standard NaN/Infinity values by
default and silently overwrites duplicate object keys. Authority-relevant JSON
must instead be finite, duplicate-free, and deterministically serializable.
"""
from __future__ import annotations

import json
import pathlib
from typing import Any, Iterable


def _reject_constant(value: str):
    raise ValueError(f"non-finite JSON constant forbidden: {value}")


def _unique_pairs(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON object key forbidden: {key}")
        out[key] = value
    return out


def loads(text: str) -> Any:
    return json.loads(
        text,
        parse_constant=_reject_constant,
        object_pairs_hook=_unique_pairs,
    )


def load(path: str | pathlib.Path) -> Any:
    return loads(pathlib.Path(path).read_text(encoding="utf-8"))


def dumps(value: Any, **kwargs) -> str:
    if "allow_nan" in kwargs and kwargs["allow_nan"] is not False:
        raise ValueError("strict JSON encoding requires allow_nan=False")
    kwargs["allow_nan"] = False
    return json.dumps(value, **kwargs)


def canonical_dumps(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def pretty_dumps(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        indent=2,
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"


def dump(path: str | pathlib.Path, value: Any, *, pretty: bool = True) -> None:
    text = pretty_dumps(value) if pretty else canonical_dumps(value)
    pathlib.Path(path).write_text(text, encoding="utf-8")
