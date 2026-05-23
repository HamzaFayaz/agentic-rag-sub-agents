import io
import re
from pathlib import Path

from pypdf import PdfReader

from app.config import settings


class ChunkService:
    def extract_text(self, filename: str, content: bytes) -> str:
        suffix = Path(filename).suffix.lower()
        if suffix in {".txt", ".md"}:
            return content.decode("utf-8", errors="replace").strip()
        if suffix == ".pdf":
            return self._extract_pdf_text(content)
        raise ValueError(f"Unsupported file type: {suffix or 'unknown'}")

    def _extract_pdf_text(self, content: bytes) -> str:
        reader = PdfReader(io.BytesIO(content))
        parts: list[str] = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
        combined = "\n".join(parts).strip()
        if not combined:
            raise ValueError("PDF contains no extractable text")
        return combined

    def split_text(self, text: str) -> list[str]:
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return []

        size = settings.chunk_size
        overlap = settings.chunk_overlap
        if overlap >= size:
            overlap = max(0, size // 4)

        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(text):
                break
            start = end - overlap

        return chunks

    def chunk_file(self, filename: str, content: bytes) -> list[str]:
        text = self.extract_text(filename, content)
        return self.split_text(text)
