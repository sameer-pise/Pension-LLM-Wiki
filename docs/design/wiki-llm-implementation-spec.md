# Wiki LLM Implementation Specification

## 1. Purpose
This specification defines the build requirements for the Wiki LLM ingestion and retrieval pipeline so engineering can implement with deterministic behavior, traceability, and measurable quality.

## 2. Scope
In scope:
- Internal web crawling (recursive, domain-scoped)
- Markdown raw storage with metadata
- PDF download and conversion to Markdown
- YouTube transcript raw extraction pipeline
- Structured logging and checkpoint-resume
- Data contracts and status flows

Out of scope:
- UI/portal features
- Advanced agent orchestration
- Embedding/vector database layer (current phase)

## 3. Design Principles
- Keep pipeline simple and deterministic.
- Invest heavily in data quality and evaluation loops.
- Add complexity only when metrics prove value.

## 4. System Components
### 4.1 Crawler Engine
Responsibilities:
- BFS traversal over internal links
- URL canonicalization
- Domain/path filtering
- Retry/backoff on fetch failures
- Link classification: internal HTML, YouTube, PDF, external, unsupported file

### 4.2 Storage Writer
Responsibilities:
- Deterministic URL to file path mapping
- YAML frontmatter generation
- Atomic writes (temp file then rename)
- Content hash-based update detection

### 4.3 Document Processor
Responsibilities:
- Download PDF documents
- Convert PDF to Markdown
- Write converted artifacts with provenance metadata
- Skip non-PDF files and log warnings

### 4.4 YouTube Transcript Processor
Responsibilities:
- Process discovered YouTube URLs by video id
- Save metadata.json, raw_segments.jsonl, status.json
- Captions priority: manual, auto, then Whisper fallback
- Delete temporary audio after Whisper transcription

### 4.5 Observability Module
Responsibilities:
- Structured JSONL logs per event
- Error recording
- Crawl checkpoint persistence
- Resume support after restart

## 5. Runtime Workflow
1. Load config and prior checkpoint state.
2. Initialize queue with canonical seed URLs.
3. Process each URL in BFS order.
4. Save page content as raw Markdown.
5. Classify discovered links and dispatch:
   - Internal HTML -> enqueue if unseen
   - PDF -> download + convert to Markdown
   - Non-PDF document -> skip + warning log
   - YouTube -> transcript extraction workflow
   - External -> skip + info log
6. Save checkpoint every N processed URLs and on graceful exit.
7. Emit final summary metrics and status.

## 6. Data Contracts

### 6.1 Raw Markdown Frontmatter (minimum)
- schema_version: string
- source_url: string
- source_domain: string
- source_hash: string
- crawl_id: string
- crawled_at_utc: ISO-8601 string
- status: raw_crawled
- content_type: page|pdf|youtube_transcript
- parent_url: optional string
- tags: list of strings

### 6.2 PDF Converted Markdown Frontmatter (minimum)
- schema_version
- source_url
- source_type: pdf
- downloaded_at_utc
- converted_at_utc
- converter_name
- converter_version
- source_file_sha256
- status: raw_crawled

### 6.3 YouTube Raw Segment JSONL record
- id
- video_id
- source_url
- start
- end
- text
- language
- method: youtube_manual_caption|youtube_auto_caption|whisper

### 6.4 Status File Contract
- id: url hash or video id
- source_url
- status: discovered|processing|whisper_required|raw_saved|failed
- updated_at_utc
- error: optional object

## 7. Canonicalization Rules
- Scheme and host lowercased
- Remove fragments
- Resolve relative links against parent URL
- Remove tracking query params
- Normalize trailing slash policy
- Only http/https accepted

## 8. File Layout Standard
- Obsidian/Vault/raw/... for page and converted content
- crawler/logs/crawl-YYYYMMDD.jsonl for logs
- crawler/state.json for checkpoint
- storage/youtube/{video_id}/metadata.json
- storage/youtube/{video_id}/raw_segments.jsonl
- storage/youtube/{video_id}/status.json
- storage/youtube/{video_id}/errors.jsonl

## 9. Error Handling and Retries
- Retries for transient network failures: max_retries with exponential backoff
- Terminal failures recorded in failed set and logs
- Crawl must continue after per-URL failure
- Non-supported documents are skipped, never fatal

## 10. Logging Specification
Required event fields:
- timestamp
- level
- event
- crawl_id
- url
- parent_url (if any)
- depth
- status
- details

Required events:
- url_fetch_started
- url_fetch_succeeded
- url_saved_markdown
- external_link_skipped
- pdf_downloaded
- pdf_converted_to_markdown
- unsupported_document_skipped
- youtube_discovered
- youtube_status_updated
- url_failed
- crawl_checkpoint_saved

## 11. Checkpoint and Resume
- Persist queue, seen, failed, counters, and crawl_id.
- Checkpoint interval configurable (default every 25 URLs).
- Resume loads checkpoint and continues from queue head.

## 12. Non-Functional Requirements
- Deterministic output for same input and same configuration
- Idempotent rerun behavior
- No duplicate processing of canonical URLs
- Traceability from derived artifact to source URL and crawl timestamp
- Crash-safe writes (no partial/corrupt markdown outputs)

## 13. Security and Compliance
- Respect robots policy if enabled by configuration
- Domain allowlist enforcement mandatory
- User-Agent must be explicit and controlled
- Source licensing/copyright constraints must be preserved in metadata

## 14. Configuration Keys (minimum)
- seed_urls
- allowed_domains
- allowed_paths
- max_depth
- max_pages
- request_timeout_seconds
- max_retries
- backoff_seconds
- checkpoint_interval
- enable_robots_check
- youtube_whisper_enabled

## 15. Delivery Milestones
M1 Foundation:
- BFS crawler, canonicalization, markdown write, dedupe

M2 Reliability:
- retries, backoff, checkpoint-resume, structured logs

M3 Documents and YouTube:
- PDF conversion path + unsupported skip logging
- YouTube raw transcript extraction with status flow

M4 Quality Gates:
- schema validation, metrics dashboard output, regression tests

## 16. Definition of Done
A release is complete only if:
- All required contracts are implemented and validated.
- Acceptance criteria in wiki-llm-acceptance-criteria.md pass.
- End-to-end run finishes with no blocker severity errors.
- Determinism checks pass across two identical dry runs.
