"""Helpers for normalizing repository references."""
from __future__ import annotations

import re

_URL_RE = re.compile(r"github\.com[:/]+([^/]+)/([^/#?]+?)(?:\.git)?/?$")
_SLUG_RE = re.compile(r"^([\w.-]+)/([\w.-]+)$")


def normalize_repo(reference: str) -> tuple[str, str]:
    """Return (full_name, clone_url) from an 'owner/name' slug or a GitHub URL.

    Raises ValueError if the reference can't be parsed.
    """
    reference = reference.strip()
    m = _URL_RE.search(reference)
    if not m:
        m = _SLUG_RE.match(reference)
    if not m:
        raise ValueError(
            "Expected 'owner/name' or a GitHub URL, e.g. 'tiangolo/fastapi'."
        )
    owner, name = m.group(1), m.group(2)
    full_name = f"{owner}/{name}"
    clone_url = f"https://github.com/{full_name}.git"
    return full_name, clone_url
