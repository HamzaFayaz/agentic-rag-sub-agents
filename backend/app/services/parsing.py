"""Document parser — Docling-based with pypdf/plain-text fallback."""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

logger = logging.getLogger(__name__)


@dataclass
class OutlineEntry:
    title: str
    level: int
    start_char: int
    end_char: int


@dataclass
class ParseStats:
    heading_count: int = 0
    max_section_tokens: int = 0
    page_count: int = 0
    language: str | None = None
    title_guess: str | None = None
    has_text: bool = False


@dataclass
class ParseResult:
    text: str
    outline: list[OutlineEntry] = field(default_factory=list)
    stats: ParseStats = field(default_factory=ParseStats)


def estimate_tokens(text: str) -> int:
    return len(text) // 4


def _compute_section_stats(
    text: str, outline: list[OutlineEntry]
) -> tuple[int, int]:
    """Return (heading_count, max_section_tokens)."""
    if not outline:
        return 0, estimate_tokens(text)

    max_tokens = 0
    for i, entry in enumerate(outline):
        end = outline[i + 1].start_char if i + 1 < len(outline) else len(text)
        section_text = text[entry.start_char : end]
        max_tokens = max(max_tokens, estimate_tokens(section_text))
    return len(outline), max_tokens


# ---------------------------------------------------------------------------
# Docling helpers
# ---------------------------------------------------------------------------

def _parse_with_docling(content: bytes, suffix: str) -> ParseResult | None:
    """Try docling conversion. Returns None on any failure."""
    try:
        from docling.document_converter import DocumentConverter
    except Exception:
        logger.debug("docling not available, skipping")
        return None

    import tempfile
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=suffix, delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        converter = DocumentConverter()
        result = converter.convert(tmp_path)
        doc = result.document

        text = doc.export_to_markdown()
        if not text or not text.strip():
            return None

        text = text.strip()
        outline = _extract_outline_from_markdown(text)
        heading_count, max_section_tokens = _compute_section_stats(text, outline)

        title_guess = _guess_title(outline, text)
        lang = getattr(doc, "language", None)

        stats = ParseStats(
            heading_count=heading_count,
            max_section_tokens=max_section_tokens,
            page_count=getattr(doc, "num_pages", 0) or 0,
            language=lang if isinstance(lang, str) else None,
            title_guess=title_guess,
            has_text=True,
        )
        return ParseResult(text=text, outline=outline, stats=stats)

    except Exception as exc:
        logger.warning("docling conversion failed: %s", exc)
        return None
    finally:
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                pass


def _extract_outline_from_markdown(text: str) -> list[OutlineEntry]:
    """Extract heading entries from markdown-formatted text."""
    import re

    entries: list[OutlineEntry] = []
    for m in re.finditer(r"^(#{1,6})\s+(.+)$", text, re.MULTILINE):
        level = len(m.group(1))
        title = m.group(2).strip()
        entries.append(
            OutlineEntry(
                title=title,
                level=level,
                start_char=m.start(),
                end_char=m.end(),
            )
        )

    if entries:
        for i, entry in enumerate(entries):
            end = entries[i + 1].start_char if i + 1 < len(entries) else len(text)
            entries[i] = OutlineEntry(
                title=entry.title,
                level=entry.level,
                start_char=entry.start_char,
                end_char=end,
            )
    return entries


# ---------------------------------------------------------------------------
# Fallback parsers
# ---------------------------------------------------------------------------

def _parse_pdf_pypdf(content: bytes) -> ParseResult:
    reader = PdfReader(io.BytesIO(content))
    parts: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            parts.append(page_text)
    combined = "\n".join(parts).strip()
    if not combined:
        raise ValueError("PDF contains no extractable text")

    outline = _extract_outline_from_markdown(combined)
    heading_count, max_section_tokens = _compute_section_stats(combined, outline)

    stats = ParseStats(
        heading_count=heading_count,
        max_section_tokens=max_section_tokens,
        page_count=len(reader.pages),
        title_guess=_guess_title(outline, combined),
        has_text=True,
    )
    return ParseResult(text=combined, outline=outline, stats=stats)


def _parse_plain_text(content: bytes) -> ParseResult:
    text = content.decode("utf-8", errors="replace").strip()
    if not text:
        raise ValueError("File contains no text")

    outline = _extract_outline_from_markdown(text)
    heading_count, max_section_tokens = _compute_section_stats(text, outline)

    stats = ParseStats(
        heading_count=heading_count,
        max_section_tokens=max_section_tokens,
        title_guess=_guess_title(outline, text),
        has_text=True,
    )
    return ParseResult(text=text, outline=outline, stats=stats)


def _guess_title(
    outline: list[OutlineEntry], text: str
) -> str | None:
    for entry in outline:
        if entry.level <= 2:
            return entry.title
    first_line = text.split("\n", 1)[0].strip()
    if 3 <= len(first_line) <= 200:
        return first_line
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_DOCLING_PREFERRED = {".pdf", ".docx", ".html"}
_PLAIN_FALLBACK = {".txt", ".md"}


def parse_document(filename: str, content: bytes) -> ParseResult:
    """Parse a document, returning text + outline + stats.

    Strategy:
      - .docx / .html → docling first, fail if empty
      - .pdf → docling first, pypdf fallback
      - .txt / .md → plain-text with markdown heading detection
    """
    suffix = Path(filename).suffix.lower()

    if suffix in _DOCLING_PREFERRED or suffix == ".pdf":
        result = _parse_with_docling(content, suffix)
        if result is not None:
            return result

        if suffix == ".pdf":
            logger.info("docling failed for PDF, falling back to pypdf")
            return _parse_pdf_pypdf(content)

        if suffix in _PLAIN_FALLBACK:
            return _parse_plain_text(content)

        raise ValueError(
            f"Failed to parse {suffix} file — docling unavailable or conversion failed"
        )

    if suffix in _PLAIN_FALLBACK:
        return _parse_plain_text(content)

    raise ValueError(f"Unsupported file type: {suffix or 'unknown'}")


def build_parser_metadata(
    stats: ParseStats, chunk_strategy: str
) -> dict:
    """Build the metadata.parser dict stored on the document row."""
    return {
        "page_count": stats.page_count,
        "heading_count": stats.heading_count,
        "chunk_strategy": chunk_strategy,
        "parsed_at": datetime.now(timezone.utc).isoformat(),
        "title_guess": stats.title_guess,
        "language": stats.language,
    }
