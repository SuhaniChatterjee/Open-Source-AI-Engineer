"""Heuristic architecture mapping.

Produces an interactive "mental model" of a repo rather than a flat file list:
top-level modules, detected architectural layers, entry points, and language
mix. This is intentionally heuristic for the MVP; a full call-graph / knowledge
graph is described in docs/TRD.md section 7.
"""
from __future__ import annotations

import os
from collections import Counter

# Directory-name -> architectural role heuristics.
_LAYER_HINTS = {
    "api": "API layer",
    "routes": "API layer",
    "controllers": "API layer",
    "endpoints": "API layer",
    "models": "Data / domain models",
    "schemas": "Data / domain models",
    "entities": "Data / domain models",
    "services": "Business logic",
    "usecases": "Business logic",
    "core": "Core / config",
    "config": "Core / config",
    "components": "UI components",
    "pages": "UI / routing",
    "app": "UI / routing",
    "views": "UI / routing",
    "db": "Persistence",
    "database": "Persistence",
    "migrations": "Persistence",
    "utils": "Utilities",
    "lib": "Utilities",
    "helpers": "Utilities",
    "tests": "Tests",
    "test": "Tests",
    "middleware": "Middleware",
    "workers": "Background jobs",
    "jobs": "Background jobs",
    "hooks": "UI state / hooks",
}

_ENTRY_HINTS = {
    "main.py",
    "app.py",
    "__main__.py",
    "manage.py",
    "index.ts",
    "index.js",
    "main.ts",
    "server.ts",
    "server.js",
    "next.config.js",
    "package.json",
    "pyproject.toml",
    "dockerfile",
    "docker-compose.yml",
}


def build_architecture(root: str, rel_files: list[str], languages: dict[str, int]) -> dict:
    modules: dict[str, dict] = {}
    layers: Counter[str] = Counter()
    entry_points: list[str] = []

    for rel in rel_files:
        parts = rel.split("/")
        top = parts[0] if len(parts) > 1 else "(root)"
        mod = modules.setdefault(
            top, {"name": top, "file_count": 0, "roles": set(), "languages": Counter()}
        )
        mod["file_count"] += 1
        ext = "." + rel.rsplit(".", 1)[-1] if "." in rel else ""
        mod["languages"][ext] += 1

        for part in parts[:-1]:
            role = _LAYER_HINTS.get(part.lower())
            if role:
                mod["roles"].add(role)
                layers[role] += 1

        base = parts[-1].lower()
        if base in _ENTRY_HINTS:
            entry_points.append(rel)

    module_list = sorted(
        (
            {
                "name": m["name"],
                "file_count": m["file_count"],
                "roles": sorted(m["roles"]),
                "top_extensions": [e for e, _ in m["languages"].most_common(3)],
            }
            for m in modules.values()
        ),
        key=lambda m: m["file_count"],
        reverse=True,
    )

    return {
        "summary": _summarize(module_list, layers, languages),
        "modules": module_list,
        "layers": [
            {"role": role, "file_count": count}
            for role, count in layers.most_common()
        ],
        "entry_points": sorted(entry_points),
        "languages": [
            {"extension": ext, "file_count": count}
            for ext, count in sorted(languages.items(), key=lambda kv: -kv[1])
        ],
    }


def _summarize(modules: list[dict], layers: Counter, languages: dict[str, int]) -> str:
    top_mods = ", ".join(m["name"] for m in modules[:5]) or "the root directory"
    top_layers = ", ".join(role for role, _ in layers.most_common(4))
    lang = ", ".join(
        ext for ext, _ in sorted(languages.items(), key=lambda kv: -kv[1])[:3]
    )
    parts = [f"The project's largest modules are: {top_mods}."]
    if top_layers:
        parts.append(f"Detected architectural layers include: {top_layers}.")
    if lang:
        parts.append(f"Primary file types: {lang}.")
    return " ".join(parts)
