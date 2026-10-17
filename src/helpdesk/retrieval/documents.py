"""Load Markdown knowledge-base articles and split them into retrievable chunks."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_H2 = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    category: str
    tags: tuple[str, ...]
    body: str
    path: str


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    section: str
    text: str
    category: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def embedding_text(self) -> str:
        """Text used for indexing: title + section give the chunk context."""
        return f"{self.title} - {self.section}\n{self.text}"


def parse_document(path: Path) -> Document:
    raw = path.read_text(encoding="utf-8")
    match = _FRONTMATTER.match(raw)
    if not match:
        raise ValueError(f"{path.name}: missing YAML frontmatter")
    meta = yaml.safe_load(match.group(1)) or {}
    for key in ("id", "title"):
        if key not in meta:
            raise ValueError(f"{path.name}: frontmatter missing '{key}'")
    return Document(
        id=str(meta["id"]),
        title=str(meta["title"]),
        category=str(meta.get("category", "")),
        tags=tuple(str(t) for t in meta.get("tags", []) or []),
        body=raw[match.end() :].strip(),
        path=str(path),
    )


def load_documents(kb_dir: Path) -> list[Document]:
    docs = [parse_document(p) for p in sorted(Path(kb_dir).glob("*.md"))]
    ids = [d.id for d in docs]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ValueError(f"Duplicate KB ids: {sorted(dupes)}")
    return docs


def _split_long(text: str, max_chars: int) -> list[str]:
    """Split on paragraph boundaries so each piece is <= max_chars (when possible)."""
    if len(text) <= max_chars:
        return [text]
    pieces: list[str] = []
    current = ""
    for para in re.split(r"\n\s*\n", text):
        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) <= max_chars or not current:
            current = candidate
        else:
            pieces.append(current)
            current = para
    if current:
        pieces.append(current)
    return pieces


def chunk_document(doc: Document, max_chars: int = 1200, min_chars: int = 200) -> list[Chunk]:
    """Chunk by `##` sections; merge tiny sections into the next, split very long ones."""
    body = doc.body
    headings = list(_H2.finditer(body))
    sections: list[tuple[str, str]] = []
    intro = body[: headings[0].start()].strip() if headings else body.strip()
    intro = re.sub(r"^#\s+.*\n?", "", intro).strip()  # drop a leading H1 title
    if intro:
        sections.append(("Overview", intro))
    for i, h in enumerate(headings):
        end = headings[i + 1].start() if i + 1 < len(headings) else len(body)
        content = body[h.end() : end].strip()
        if content:
            sections.append((h.group(1).strip(), content))

    merged: list[tuple[str, str]] = []
    carry: tuple[str, str] | None = None
    for name, content in sections:
        if carry:
            name, content = f"{carry[0]} / {name}", f"{carry[1]}\n\n{content}"
            carry = None
        if len(content) < min_chars:
            carry = (name, content)
        else:
            merged.append((name, content))
    if carry:
        if merged:
            last_name, last_content = merged.pop()
            merged.append((f"{last_name} / {carry[0]}", f"{last_content}\n\n{carry[1]}"))
        else:
            merged.append(carry)

    chunks: list[Chunk] = []
    for name, content in merged:
        for piece in _split_long(content, max_chars):
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.id}#{len(chunks) + 1}",
                    doc_id=doc.id,
                    title=doc.title,
                    section=name,
                    text=piece,
                    category=doc.category,
                    tags=doc.tags,
                )
            )
    return chunks


def load_chunks(kb_dir: Path, max_chars: int = 1200) -> list[Chunk]:
    return [c for d in load_documents(kb_dir) for c in chunk_document(d, max_chars=max_chars)]
