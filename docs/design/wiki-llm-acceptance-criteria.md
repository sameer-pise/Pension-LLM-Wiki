# Wiki LLM Acceptance Criteria

## 1. Crawl and Discovery
- Given valid seed URLs, crawler discovers internal links recursively until queue exhaustion or limits are reached.
- External links are never downloaded.
- Canonically equivalent URLs are processed once only.

## 2. Raw Page Storage
- Every successfully crawled page produces one Markdown file with required frontmatter fields.
- Re-crawl of unchanged source content does not produce duplicate or unnecessary rewrites.

## 3. PDF Handling
- PDF links are downloaded and converted to Markdown.
- Non-PDF document links are skipped.
- Skip action logs include link_url, parent_url, extension, reason, action.

## 4. YouTube Handling
- YouTube links create per-video storage folder.
- Metadata is saved to metadata.json.
- Transcript extraction order is manual captions, auto captions, Whisper fallback.
- Temporary audio is deleted after Whisper transcription.
- raw_segments.jsonl stores one segment per line with preserved timestamps.

## 5. Logging
- Logs are JSONL and contain required fields for all major events.
- Failures include actionable error details and source URL.

## 6. Checkpoint and Resume
- Interrupting crawl and resuming continues from saved queue state.
- Seen/failed state is preserved across restart.

## 7. Determinism and Idempotency
- Two runs with identical inputs and config produce the same artifact set and metadata (except runtime timestamps).
- Rerun does not duplicate files for already processed canonical URLs.

## 8. Data Quality Gates
- Metadata completeness >= 99% on required fields.
- Schema validation pass rate >= 99% for generated artifacts.
- Crawl success rate threshold configurable, default target >= 95% excluding blocked URLs.

## 9. Operational Safety
- max_depth and max_pages limits are enforced.
- Retry and backoff are enforced on transient fetch failures.
- Unsupported schemes are rejected.

## 10. Exit Criteria for Production Readiness
- No open High severity defects in crawler, storage, or transcript pipelines.
- End-to-end integration test suite passes.
- Observability outputs available for troubleshooting and post-run audit.
