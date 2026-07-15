"""Structure-aware chunking.

Uses Tree-sitter to split Python / TypeScript / JavaScript source into
semantically meaningful chunks (functions, classes, methods) when available.
Falls back to a robust line-window chunker for Markdown and whenever
Tree-sitter is not importable — so indexing always works.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    path: str  # repo-relative path
    start_line: int
    end_line: int
    kind: str  # function | class | method | block | doc
    name: str
    text: str


# --- Tree-sitter setup (best-effort) ------------------------------------------

_TS_LANGS: dict[str, object] = {}
_TS_AVAILABLE = False

try:  # pragma: no cover - depends on installed wheels
    from tree_sitter import Language, Parser
    import tree_sitter_python as tspython
    import tree_sitter_typescript as tstypescript

    _TS_LANGS = {
        "python": Language(tspython.language()),
        "typescript": Language(tstypescript.language_typescript()),
        "tsx": Language(tstypescript.language_tsx()),
    }
    _TS_AVAILABLE = True
except Exception as exc:  # pragma: no cover
    logger.warning("Tree-sitter unavailable (%s); using line-window chunker", exc)


_EXT_LANG = {
    ".py": "python",
    ".ts": "typescript",
    ".js": "typescript",  # close enough for grammar-based splitting
    ".jsx": "tsx",
    ".tsx": "tsx",
}

# Node types that make good standalone chunks per grammar.
_DEF_NODES = {
    "python": {"function_definition", "class_definition"},
    "typescript": {
        "function_declaration",
        "class_declaration",
        "method_definition",
        "lexical_declaration",
        "export_statement",
    },
    "tsx": {
        "function_declaration",
        "class_declaration",
        "method_definition",
        "lexical_declaration",
        "export_statement",
    },
}


def chunk_file(rel_path: str, source: str) -> list[Chunk]:
    ext = "." + rel_path.rsplit(".", 1)[-1] if "." in rel_path else ""
    lang = _EXT_LANG.get(ext)
    if _TS_AVAILABLE and lang in _TS_LANGS:
        try:
            return _chunk_with_treesitter(rel_path, source, lang)
        except Exception as exc:  # pragma: no cover
            logger.debug("tree-sitter chunk failed for %s (%s)", rel_path, exc)
    return _chunk_by_lines(rel_path, source)


def _node_name(node, source_bytes: bytes) -> str:
    for child in node.children:
        if child.type in ("identifier", "type_identifier", "property_identifier"):
            return source_bytes[child.start_byte : child.end_byte].decode(
                "utf-8", "replace"
            )
    return "<anonymous>"


def _chunk_with_treesitter(rel_path: str, source: str, lang: str) -> list[Chunk]:
    from tree_sitter import Parser

    parser = Parser(_TS_LANGS[lang])
    source_bytes = source.encode("utf-8", "replace")
    tree = parser.parse(source_bytes)
    def_types = _DEF_NODES[lang]

    chunks: list[Chunk] = []

    def visit(node) -> None:
        if node.type in def_types:
            text = source_bytes[node.start_byte : node.end_byte].decode(
                "utf-8", "replace"
            )
            if text.strip():
                chunks.append(
                    Chunk(
                        path=rel_path,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        kind=node.type.split("_")[0],
                        name=_node_name(node, source_bytes),
                        text=text[:4000],
                    )
                )
            return  # don't double-index nested defs as separate top-level chunks
        for child in node.children:
            visit(child)

    visit(tree.root_node)

    if not chunks:  # file had no top-level defs (e.g. a script); fall back
        return _chunk_by_lines(rel_path, source)
    return chunks


def _chunk_by_lines(rel_path: str, source: str, window: int = 60, overlap: int = 10) -> list[Chunk]:
    lines = source.splitlines()
    if not lines:
        return []
    kind = "doc" if rel_path.lower().endswith(".md") else "block"
    chunks: list[Chunk] = []
    step = max(1, window - overlap)
    for start in range(0, len(lines), step):
        window_lines = lines[start : start + window]
        text = "\n".join(window_lines).strip()
        if not text:
            continue
        chunks.append(
            Chunk(
                path=rel_path,
                start_line=start + 1,
                end_line=min(start + window, len(lines)),
                kind=kind,
                name=rel_path.rsplit("/", 1)[-1],
                text=text[:4000],
            )
        )
    return chunks
