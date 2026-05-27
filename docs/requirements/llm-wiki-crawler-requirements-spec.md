
# LLM Wiki Crawler Requirements Specification

## Related Documents
- [LLM Wiki Structure Config Requirements](llm-wiki-structure-config-requirements-spec.md)
- [LLM Wiki Raw-to-Wiki Structuring Requirements](llm-wiki-raw-to-wiki-structuring-requirements-spec.md)
- [LLM Wiki Crawler Design](../design/llm-wiki-crawler-design.md)
- [Wiki LLM Acceptance Criteria](../design/wiki-llm-acceptance-criteria.md)

## 1. Document Control
- Document title: LLM Wiki Crawler Requirements Specification
- Version: 1.0
- Date: 2026-05-27
- Status: Approved for implementation
- Related design documents:
  - ../design/llm-wiki-crawler-design.md
  - ../design/llm-wiki-markdown-storage-design.md
  - ../design/redis-queue-design-spec.md
  - ../design/wiki-llm-implementation-spec.md

## 2. Purpose
Define clear, testable requirements for the LLM Wiki crawler so engineering teams can implement a deterministic, reliable, and auditable pipeline for web pages, PDFs, and YouTube links.

## 3. Scope
In scope:
- Internal domain crawling using BFS.
- Recursive link discovery with canonical URL deduplication.
- Raw markdown storage with metadata.
- PDF download and conversion to markdown.
- YouTube raw transcript extraction handoff.
- Structured logging, checkpointing, and resume.

Out of scope:
- UI features.
- Human editorial workflow tooling.
- Embedding/vector index implementation.

## 4. Design Principles
- Keep the pipeline simple and deterministic.
- Prioritize data quality and evaluation loops.
- Add complexity only when metrics justify it.

## 5. System Context
Input:
- Seed URLs from configuration/taxonomy.

Processing:
- URL crawl and classification.
- Dispatch to page/PDF/YouTube handling paths.

Output:
- Raw markdown artifacts.
- Converted PDF markdown artifacts.
- YouTube transcript raw artifacts.
- Structured logs and status/checkpoint files.

## 6. Functional Requirements

| ID | Category | Requirement Statement | Acceptance Criteria |
|---|---|---|---|
| FR-001 | Discovery and Crawl | The crawler shall process seed URLs using BFS traversal. | AC-001 |
| FR-002 | Discovery and Crawl | The crawler shall canonicalize each URL before deduplication and enqueue. | AC-003 |
| FR-003 | Discovery and Crawl | The crawler shall process each canonical internal URL at most once per crawl run. | AC-001 |
| FR-004 | Discovery and Crawl | The crawler shall follow only internal domain links that pass allowed path policy. | AC-002 |
| FR-005 | Discovery and Crawl | The crawler shall ignore external links and log skip events. | AC-002 |
| FR-006 | Content Extraction and Storage | The crawler shall extract main page content and save as markdown. | AC-004 |
| FR-007 | Content Extraction and Storage | The crawler shall write YAML frontmatter with required metadata fields. | AC-004 |
| FR-008 | Content Extraction and Storage | The crawler shall write outputs atomically to avoid partial/corrupt files. | AC-005 |
| FR-009 | Content Extraction and Storage | The crawler shall compare content hash and skip unnecessary rewrites. | AC-006 |
| FR-010 | Document Handling | The crawler shall detect document links during link classification. | AC-007, AC-008 |
| FR-011 | Document Handling | The crawler shall process PDF links by downloading and converting to markdown. | AC-007 |
| FR-012 | Document Handling | The crawler shall skip non-PDF document links. | AC-008 |
| FR-013 | Document Handling | The crawler shall log non-PDF skips with link_url, parent_url, extension, reason, and action. | AC-008 |
| FR-014 | YouTube Handling | The crawler shall detect YouTube URLs and route to transcript processing pipeline. | AC-009 |
| FR-015 | YouTube Handling | The transcript workflow shall persist metadata.json, raw_segments.jsonl, and status.json per video id. | AC-009 |
| FR-016 | YouTube Handling | Transcript extraction order shall be manual captions, auto captions, then Whisper fallback. | AC-010 |
| FR-017 | YouTube Handling | Temporary audio files shall be deleted after Whisper transcription. | AC-011 |
| FR-018 | Reliability and State | The crawler shall retry transient fetch failures with exponential backoff. | AC-012 |
| FR-019 | Reliability and State | The crawler shall checkpoint queue, seen, failed, counters, and crawl_id. | AC-013 |
| FR-020 | Reliability and State | The crawler shall resume from checkpoint on restart. | AC-013 |
| FR-021 | Reliability and State | Terminal failures shall be logged without aborting the full crawl run. | AC-014 |
| FR-022 | Logging and Observability | The crawler shall emit structured JSONL logs. | AC-015 |
| FR-023 | Logging and Observability | Every log event shall include timestamp, level, event, crawl_id, url, status, and details. | AC-015 |
| FR-024 | Logging and Observability | Queue and worker events shall be logged for debugging and audit. | AC-016 |

## 7. Non-Functional Requirements

| ID | Quality Attribute | Requirement Statement | Acceptance Criteria |
|---|---|---|---|
| NFR-001 | Determinism | Identical inputs and config shall produce equivalent artifact sets. | AC-017 |
| NFR-002 | Idempotency | Reruns shall not create duplicate artifacts. | AC-018 |
| NFR-003 | Performance | Crawler shall maintain responsive enqueue and discovery under heavy PDF/YouTube workloads. | Monitored via perf tests |
| NFR-004 | Scalability | Architecture shall support queue-based worker scaling. | Verified in load test |
| NFR-005 | Traceability | Every derived artifact shall retain source provenance. | AC-019 |
| NFR-006 | Security | Only allowed domains and schemes are processed. | Security and policy test |
| NFR-007 | Reliability | Pipeline shall continue after per-item failures. | AC-020 |

## 8. Data Contract Requirements

### 8.1 Raw Page Frontmatter (minimum)
- schema_version
- title
- source_url
- source_domain
- source_hash
- crawled_at_utc
- crawl_id
- status
- content_type
- parent_url (optional)
- tags

### 8.2 Non-PDF Skip Log Event (minimum)
- event: unsupported_document_skipped
- link_url
- parent_url
- extension
- reason: unsupported_document_type
- action: skipped

### 8.3 YouTube Segment Record (minimum)
- id
- video_id
- source_url
- start
- end
- text
- language
- method

## 9. Configuration Requirements
- CFG-001: seed_urls
- CFG-002: allowed_domains
- CFG-003: allowed_paths
- CFG-004: max_depth
- CFG-005: max_pages
- CFG-006: request_timeout_seconds
- CFG-007: max_retries
- CFG-008: backoff_seconds
- CFG-009: checkpoint_interval
- CFG-010: youtube_whisper_enabled

## 10. Error Handling Requirements
- ERR-001: Invalid URL formats shall be skipped and logged.
- ERR-002: Unsupported schemes shall be rejected and logged.
- ERR-003: Non-retryable failures shall move to terminal failure state immediately.
- ERR-004: Retry-exhausted failures shall be recorded for replay analysis.

## 11. Acceptance Criteria Matrix

| AC ID | Area | Mapped Requirements | Acceptance Criteria |
|---|---|---|---|
| AC-001 | Crawl and Discovery | FR-001, FR-003 | Given valid seed URLs, crawler traverses URLs in BFS order and processes each canonical URL once. |
| AC-002 | Crawl and Discovery | FR-004, FR-005 | External links are never crawled and are logged as skipped. |
| AC-003 | Crawl and Discovery | FR-002 | Canonical URL variants do not create duplicate crawl jobs. |
| AC-004 | Storage and Integrity | FR-006, FR-007 | Every successful page crawl outputs one markdown file with required frontmatter. |
| AC-005 | Storage and Integrity | FR-008 | No partially written markdown file is present after forced interruption test. |
| AC-006 | Storage and Integrity | FR-009 | Unchanged content is not rewritten on rerun. |
| AC-007 | PDF and Document Handling | FR-011 | PDF links are downloaded and converted to markdown. |
| AC-008 | PDF and Document Handling | FR-012, FR-013 | Non-PDF links are skipped with required warning fields. |
| AC-009 | YouTube Handling | FR-014, FR-015 | YouTube links produce per-video metadata/status/transcript artifacts. |
| AC-010 | YouTube Handling | FR-016 | Caption source priority is manual then auto then Whisper. |
| AC-011 | YouTube Handling | FR-017 | Temporary audio is removed after Whisper run. |
| AC-012 | Reliability and Resume | FR-018 | Transient network failures trigger exponential-backoff retries. |
| AC-013 | Reliability and Resume | FR-019, FR-020 | Restart resumes from checkpoint with queue/seen continuity. |
| AC-014 | Reliability and Resume | FR-021 | Single URL failure does not stop full crawl. |
| AC-015 | Logging and Auditability | FR-022, FR-023 | Logs are JSONL and include required core fields. |
| AC-016 | Logging and Auditability | FR-024 | Queue dispatch and worker outcomes are traceable by crawl_id and job identifiers. |
| AC-017 | Non-Functional Quality Gates | NFR-001 | Two identical dry runs produce equivalent artifact inventory and hashes (excluding runtime timestamps). |
| AC-018 | Non-Functional Quality Gates | NFR-002 | No duplicate artifact creation for already processed canonical URLs. |
| AC-019 | Non-Functional Quality Gates | NFR-005 | Every artifact includes source provenance fields. |
| AC-020 | Non-Functional Quality Gates | NFR-007 | End-to-end run completes despite bounded per-item failures. |

## 12. Test Strategy
- Unit tests:
  - URL canonicalization
  - link classification
  - retry/backoff behavior
  - frontmatter schema validation
- Integration tests:
  - crawl + storage path
  - PDF conversion path
  - YouTube transcript path
  - checkpoint/resume flow
- Regression tests:
  - deterministic rerun checks
  - duplicate prevention checks

## 13. Definition of Done
A crawler release is accepted only when:
- All applicable FR/NFR requirements are implemented.
- AC-001 to AC-020 pass.
- No open High severity defects.
- Runbook exists for failures, retries, and replay.
