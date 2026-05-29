## Module 3: Record Manager

Content-aware document ingestion with:

- SHA-256 hashing over full file bytes
- Skip re-upload when filename and hash match (`ingest_action: unchanged` — no chunk/embed work)
- Update in place when filename matches but content changed (`ingest_action: updated` — same document `id`)
- Supabase migration `003_record_manager.sql` (`content_hash`, unique `user_id` + `filename`)
- Upload API exposes `ingest_action`, `content_hash`, and `updated_at`
- Documents UI upload outcomes (Uploaded / Already indexed / Updated)

## Chat & UI

- Dark mode with system preference and header toggle
- ChatGPT-style empty state: centered welcome input until the first message, then bottom input bar
- ChatGPT-style messages: assistant text on the canvas (no boxed bubbles), subtle user pills, muted source chips
- README and PROGRESS updated; Module 3 validated E2E

## Setup note

Apply `supabase/migrations/003_record_manager.sql` in the Supabase SQL Editor before testing upload deduplication.
