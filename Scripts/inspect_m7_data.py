"""
Inspect documents + document_chunks for Module 7 (Text-to-SQL) discussion.

Loads backend/.env. One of these auth paths is required:

  1. SUPABASE_SERVICE_ROLE_KEY  — bypasses RLS (dev/admin inspect)
  2. SUPABASE_DEV_EMAIL + SUPABASE_DEV_PASSWORD — signs in; sees your rows via RLS

Run:
  backend\\venv\\Scripts\\python.exe Scripts\\inspect_m7_data.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client

ROOT = Path(__file__).resolve().parents[1]


def load_backend_env() -> Path:
    """Load backend/.env (same vars as FastAPI app: SUPABASE_URL, etc.)."""
    candidates = [
        ROOT / "backend" / ".env",
        Path.cwd() / ".env",  # when cwd is backend/
        Path.cwd() / "backend" / ".env",
    ]
    for path in candidates:
        if path.is_file():
            load_dotenv(path, override=True)
            return path.resolve()
    print(
        "Could not find backend/.env. Tried:\n"
        + "\n".join(f"  - {p}" for p in candidates),
        file=sys.stderr,
    )
    sys.exit(1)


ENV_PATH = load_backend_env()
URL = os.environ.get("SUPABASE_URL", "").strip()
ANON = os.environ.get("SUPABASE_ANON_KEY", "").strip()
SERVICE = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
DEV_EMAIL = os.environ.get("SUPABASE_DEV_EMAIL", "").strip()
DEV_PASSWORD = os.environ.get("SUPABASE_DEV_PASSWORD", "").strip()


def j(obj) -> str:
    return json.dumps(obj, indent=2, default=str)


def make_client() -> tuple[Client, str]:
    if not URL or not ANON:
        print("Missing SUPABASE_URL or SUPABASE_ANON_KEY in backend/.env", file=sys.stderr)
        sys.exit(1)

    if SERVICE:
        return create_client(URL, SERVICE), "service_role"

    client = create_client(URL, ANON)
    if DEV_EMAIL and DEV_PASSWORD:
        session = client.auth.sign_in_with_password(
            {"email": DEV_EMAIL, "password": DEV_PASSWORD}
        )
        token = session.session.access_token
        client.postgrest.auth(token)
        return client, f"user ({DEV_EMAIL})"

    print(
        "Cannot read documents: RLS blocks the anon key.\n"
        "Add ONE of these to backend/.env and rerun:\n"
        "  SUPABASE_SERVICE_ROLE_KEY=...   (Dashboard → Settings → API → service_role)\n"
        "  SUPABASE_DEV_EMAIL=...          (your app login)\n"
        "  SUPABASE_DEV_PASSWORD=...\n",
        file=sys.stderr,
    )
    sys.exit(1)


def main() -> None:
    print(f"Env file: {ENV_PATH}")
    print(f"SUPABASE_URL: {URL}\n")

    client, auth_mode = make_client()
    print(f"Auth: {auth_mode}\n")

    docs = (
        client.table("documents")
        .select(
            "id, filename, status, mime_type, byte_size, content_hash, "
            "created_at, metadata"
        )
        .order("created_at")
        .execute()
    )
    rows = docs.data or []
    print(f"=== documents ({len(rows)} rows) ===")
    print(j(rows))

    if not rows:
        print("\nNo documents found for this auth context.")
        sys.exit(0)

    doc_ids = [r["id"] for r in rows]

    chunks = (
        client.table("document_chunks")
        .select(
            "id, document_id, chunk_index, section_title, heading_level, "
            "chunk_level, parent_id, token_count, content"
        )
        .in_("document_id", doc_ids)
        .order("document_id")
        .order("chunk_index")
        .execute()
    )
    chunk_rows = chunks.data or []
    for c in chunk_rows:
        text = c.get("content") or ""
        c["content_preview"] = text[:120] + ("…" if len(text) > 120 else "")
        del c["content"]

    print(f"\n=== document_chunks ({len(chunk_rows)} rows) ===")
    print(j(chunk_rows))

    counts: dict[str, int] = {}
    for c in chunk_rows:
        did = c["document_id"]
        counts[did] = counts.get(did, 0) + 1

    print("\n=== SQL-style aggregates (Text-to-SQL answers these) ===")
    print(f"  COUNT(documents)           = {len(rows)}")
    print(f"  COUNT(document_chunks)     = {len(chunk_rows)}")
    for d in rows:
        llm = (d.get("metadata") or {}).get("llm") or {}
        parser = (d.get("metadata") or {}).get("parser") or {}
        print(f"\n  File: {d['filename']}")
        print(f"    status: {d['status']}, byte_size: {d['byte_size']}")
        print(f"    chunk_count: {counts.get(d['id'], 0)}")
        print(f"    doc_type (metadata.llm): {llm.get('doc_type')}")
        print(f"    topics (metadata.llm): {llm.get('topics')}")
        print(f"    chunk_strategy (metadata.parser): {parser.get('chunk_strategy')}")

    print("\n=== RAG vs SQL on this data ===")
    print("  RAG  → searches document_chunks.content (text passages)")
    print("  SQL  → counts/filters documents + metadata + chunk counts (structured rows)")
    print("\n  Example RAG:  'What companies did Hamza work at?' → chunk text")
    print("  Example SQL:  'How many chunks in my CV?' → COUNT on document_chunks")
    print("  Example SQL:  'List doc_type for each file' → metadata->llm->doc_type")


if __name__ == "__main__":
    main()
