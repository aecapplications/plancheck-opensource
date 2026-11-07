"""Per-book extraction prompts.

prompts.get(name) returns the prompt module for a book's `prompts_module`
name (see webapp/books.py). Book-neutral scaffolding (classification) lives
in prompts.base.
"""
from __future__ import annotations

from types import ModuleType

from . import base, cbc, cec, crc

_MODULES: dict[str, ModuleType] = {"crc": crc, "cec": cec, "cbc": cbc}


def get(name: str) -> ModuleType:
    return _MODULES[name]
