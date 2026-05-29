"""Structure-aware chunking with rule-based strategy selection."""

from __future__ import annotations

import re
from typing import Any

from app.config import settings
from app.services.parsing import (
    OutlineEntry,
    ParseResult,
    ParseStats,
    build_parser_metadata,
    estimate_tokens,
    parse_document,
)

STRATEGY_FIXED = "FIXED"
STRATEGY_SECTION = "SECTION"


class ChunkService:
    """Parse documents and produce chunk dicts with structural metadata."""

    # ------------------------------------------------------------------
    # Strategy router
    # ------------------------------------------------------------------

    @staticmethod
    def choose_strategy(stats: ParseStats) -> str:
        """Pick a chunking strategy from parse stats (first match wins).

        R1: no text          → raise
        R2: heading_count < min_headings_for_section → FIXED
        R3: max_section_tokens > max_chunk_tokens    → SECTION (parent-child inside)
        R4: heading_count >= 2 and all sections fit  → SECTION
        R5: else             → FIXED
        """
        if not stats.has_text:
            raise ValueError("Document has no extractable text")

        if stats.heading_count < settings.min_headings_for_section:
            return STRATEGY_FIXED

        if stats.max_section_tokens > settings.max_chunk_tokens:
            return STRATEGY_SECTION

        if stats.heading_count >= 2:
            return STRATEGY_SECTION

        return STRATEGY_FIXED

    # ------------------------------------------------------------------
    # Fixed-size chunking
    # ------------------------------------------------------------------

    def chunk_fixed(self, text: str) -> list[dict[str, Any]]:
        """Split text into fixed-size overlapping windows."""
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return []

        size = settings.chunk_size
        overlap = settings.chunk_overlap
        if overlap >= size:
            overlap = max(0, size // 4)

        chunks: list[dict[str, Any]] = []
        start = 0
        idx = 0
        while start < len(text):
            end = min(start + size, len(text))
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(
                    {
                        "content": chunk_text,
                        "chunk_index": idx,
                        "section_title": None,
                        "heading_level": None,
                        "parent_index": None,
                        "chunk_level": None,
                        "token_count": estimate_tokens(chunk_text),
                    }
                )
                idx += 1
            if end >= len(text):
                break
            start = end - overlap
        return chunks

    # ------------------------------------------------------------------
    # Section-aware chunking (with parent-child for long sections)
    # ------------------------------------------------------------------

    def chunk_by_sections(
        self, text: str, outline: list[OutlineEntry]
    ) -> list[dict[str, Any]]:
        """Split text along heading boundaries.

        Short sections → single chunk.
        Long sections (> max_chunk_tokens) → parent + fixed-window children.
        """
        if not outline:
            return self.chunk_fixed(text)

        max_tokens = settings.max_chunk_tokens
        size = settings.chunk_size
        overlap = settings.chunk_overlap
        if overlap >= size:
            overlap = max(0, size // 4)

        chunks: list[dict[str, Any]] = []
        idx = 0

        for entry in outline:
            section_text = text[entry.start_char : entry.end_char].strip()
            if not section_text:
                continue

            section_tokens = estimate_tokens(section_text)

            if section_tokens <= max_tokens:
                chunks.append(
                    {
                        "content": section_text,
                        "chunk_index": idx,
                        "section_title": entry.title,
                        "heading_level": entry.level,
                        "parent_index": None,
                        "chunk_level": None,
                        "token_count": section_tokens,
                    }
                )
                idx += 1
            else:
                parent_idx = idx
                chunks.append(
                    {
                        "content": section_text,
                        "chunk_index": idx,
                        "section_title": entry.title,
                        "heading_level": entry.level,
                        "parent_index": None,
                        "chunk_level": "parent",
                        "token_count": section_tokens,
                    }
                )
                idx += 1

                normalized = re.sub(r"\s+", " ", section_text).strip()
                start = 0
                while start < len(normalized):
                    end = min(start + size, len(normalized))
                    child_text = normalized[start:end].strip()
                    if child_text:
                        chunks.append(
                            {
                                "content": child_text,
                                "chunk_index": idx,
                                "section_title": entry.title,
                                "heading_level": entry.level,
                                "parent_index": parent_idx,
                                "chunk_level": "child",
                                "token_count": estimate_tokens(child_text),
                            }
                        )
                        idx += 1
                    if end >= len(normalized):
                        break
                    start = end - overlap

        return chunks

    # ------------------------------------------------------------------
    # Orchestrator
    # ------------------------------------------------------------------

    def chunk_document(
        self, filename: str, content: bytes
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Parse file, choose strategy, produce chunks + parser metadata.

        Returns:
            (chunks, parser_metadata_dict)
        """
        parsed: ParseResult = parse_document(filename, content)
        strategy = self.choose_strategy(parsed.stats)

        if strategy == STRATEGY_SECTION:
            chunks = self.chunk_by_sections(parsed.text, parsed.outline)
        else:
            chunks = self.chunk_fixed(parsed.text)

        if not chunks:
            raise ValueError("No text content to index")

        metadata = build_parser_metadata(parsed.stats, strategy)
        return chunks, metadata

    # ------------------------------------------------------------------
    # Legacy helpers (kept for backward compat during migration)
    # ------------------------------------------------------------------

    def extract_text(self, filename: str, content: bytes) -> str:
        parsed = parse_document(filename, content)
        return parsed.text

    def split_text(self, text: str) -> list[str]:
        chunks = self.chunk_fixed(text)
        return [c["content"] for c in chunks]

    def chunk_file(self, filename: str, content: bytes) -> list[str]:
        text = self.extract_text(filename, content)
        return self.split_text(text)
