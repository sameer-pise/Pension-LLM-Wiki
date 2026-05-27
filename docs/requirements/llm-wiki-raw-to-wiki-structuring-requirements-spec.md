# LLM Wiki Raw-to-Wiki Structuring Requirements Specification

## 1. Document Control
- Document title: LLM Wiki Raw-to-Wiki Structuring Requirements Specification
- Version: 1.0
- Date: 2026-05-27
- Status: Approved for implementation
- Related design documents:
  - ../design/llm-wiki-crawler-design.md
  - ../design/llm-wiki-markdown-storage-design.md
  - ../design/wiki-llm-implementation-spec.md

## 2. Purpose
Define requirements for the next pipeline stage that transforms raw crawled markdown into structured wiki-ready content organized by category and sub-category, with chunked sections optimized for LLM retrieval and answer generation.

## 3. Scope
In scope:
- Read raw markdown artifacts from raw layer.
- Build structured folder hierarchy by main category and sub-category.
- Extract and clean relevant content.
- Chunk content into coherent wiki sections.
- Write wiki-ready markdown with deterministic metadata.
- Preserve provenance to original raw artifacts.

Out of scope:
- Recrawling source websites.
- LLM prompt generation.
- Embedding/vector database indexing.

## 4. Pipeline Objective
Transform noisy raw pages into consistent, structured wiki notes that are:
- easy for humans to navigate,
- semantically coherent for retrieval,
- traceable to source,
- deterministic across reruns.

## 5. Folder Structure Requirements
Target folder pattern:
- Obsidian/Vault/wiki/{main_category_slug}/{sub_category_slug}/{topic_slug}.md

Rules:
- Category and sub-category slugs must be deterministic.
- Existing reviewed notes must not be overwritten.
- Missing directories must be created automatically.

## 6. Functional Requirements

| ID | Category | Requirement Statement | Acceptance Criteria |
|---|---|---|---|
| FRS-001 | Input Discovery | The processor shall read raw markdown files from configured raw paths in taxonomy. | ACS-001 |
| FRS-002 | Metadata Parsing | The processor shall parse raw frontmatter and body sections safely even when partial/malformed. | ACS-002 |
| FRS-003 | Category Mapping | The processor shall map each raw note to main category and sub-category using taxonomy metadata. | ACS-003 |
| FRS-004 | Folder Structuring | The processor shall write outputs to deterministic wiki folder paths by category/sub-category/topic. | ACS-004 |
| FRS-005 | Noise Removal | The processor shall remove navigation and non-content noise phrases before chunking. | ACS-005 |
| FRS-006 | Content Selection | The processor shall select relevant content using topic keywords and fallback logic when confidence is low. | ACS-006 |
| FRS-007 | Chunking Strategy | The processor shall chunk content by semantic section boundaries (headings/blocks), not fixed token windows. | ACS-007 |
| FRS-008 | Chunk Limits | Each chunk shall respect configurable min/max word limits and preserve meaning continuity. | ACS-008 |
| FRS-009 | Chunk Ordering | Chunks shall preserve source order to maintain narrative context. | ACS-009 |
| FRS-010 | Wiki Composition | The processor shall assemble chunked content into wiki markdown with standard sections (Overview, Extracted Content, Related Notes, Source). | ACS-010 |
| FRS-011 | Related Notes | The processor shall generate related note links using shared sub-category and taxonomy relationships. | ACS-011 |
| FRS-012 | Provenance | The wiki note shall retain source_url, source_hash, source path, and processing timestamp. | ACS-012 |
| FRS-013 | Backup | The processor shall backup existing non-empty wiki files before overwrite. | ACS-013 |
| FRS-014 | Reviewed Protection | The processor shall skip files marked reviewed. | ACS-014 |
| FRS-015 | Status Control | The processor shall mark generated notes with deterministic status values (for example clean_draft, auto_cleaned). | ACS-015 |
| FRS-016 | Deterministic Output | With identical input and config, output structure and chunk boundaries shall be reproducible. | ACS-016 |
| FRS-017 | Error Isolation | Failures on one note shall not stop processing of remaining notes. | ACS-017 |
| FRS-018 | Logging | The processor shall emit structured logs for processed, skipped, failed, and chunking decisions. | ACS-018 |

## 7. Non-Functional Requirements

| ID | Quality Attribute | Requirement Statement | Acceptance Criteria |
|---|---|---|---|
| NFRS-001 | Determinism | Same inputs/config produce equivalent wiki artifacts and chunk boundaries. | ACS-016 |
| NFRS-002 | Idempotency | Reruns shall not create duplicate wiki files or unstable chunk IDs. | ACS-019 |
| NFRS-003 | Traceability | Every wiki note and chunk must be traceable to raw source metadata. | ACS-012 |
| NFRS-004 | Reliability | Pipeline continues when individual files fail. | ACS-017 |
| NFRS-005 | Maintainability | Chunking and cleaning rules must be configuration-driven where practical. | ACS-020 |
| NFRS-006 | Performance | Processing should scale linearly with number of notes under normal conditions. | ACS-021 |

## 8. Chunking Design Requirements

### 8.1 Chunk Unit
- Primary boundary: markdown heading blocks.
- Secondary boundary: paragraph blocks when headings are unavailable.

### 8.2 Chunk Metadata (minimum)
- chunk_id
- note_id
- main_category
- sub_category
- topic
- source_url
- source_hash
- section_heading
- chunk_order
- word_count
- status

### 8.3 Chunk Quality Rules
- Avoid splitting bullet lists mid-list.
- Avoid splitting definition paragraphs from their headings.
- Preserve numeric/rule lists as a single chunk when possible.
- Merge undersized neighboring chunks if below minimum threshold.

## 9. Wiki Note Data Contract
Minimum frontmatter fields:
- schema_version
- title
- main_category
- sub_category
- topic
- content_type
- source_url
- source_hash
- source_raw_path
- last_cleaned
- status
- tags
- related_notes

Minimum body sections:
- # Title
- ## Overview
- ## Extracted Content
- ## Related Notes
- ## Source

## 10. Configuration Requirements
- CFGS-001: raw_root_path
- CFGS-002: wiki_root_path
- CFGS-003: taxonomy_file
- CFGS-004: include_keywords_by_topic
- CFGS-005: exclude_keywords_by_topic
- CFGS-006: chunk_min_words
- CFGS-007: chunk_max_words
- CFGS-008: backup_enabled
- CFGS-009: skip_reviewed_enabled
- CFGS-010: log_level

## 11. Acceptance Criteria Matrix

| AC ID | Area | Mapped Requirements | Acceptance Criteria |
|---|---|---|---|
| ACS-001 | Input Discovery | FRS-001 | Processor discovers and loads all configured raw input notes. |
| ACS-002 | Metadata Parsing | FRS-002 | Malformed or partial frontmatter does not crash pipeline; defaults are applied and logged. |
| ACS-003 | Category Mapping | FRS-003 | Every processed note is assigned valid main category and sub-category. |
| ACS-004 | Folder Structuring | FRS-004 | Output notes are saved in deterministic category/sub-category paths. |
| ACS-005 | Noise Removal | FRS-005 | Navigation/noise phrases are absent from extracted wiki content. |
| ACS-006 | Content Selection | FRS-006 | Relevant section extraction works for keyword hits and fallback path. |
| ACS-007 | Chunking Strategy | FRS-007 | Chunks align to semantic sections rather than fixed token cuts. |
| ACS-008 | Chunk Limits | FRS-008 | Chunk sizes meet configured min/max constraints or merge rules. |
| ACS-009 | Chunk Ordering | FRS-009 | Chunk order matches source section order. |
| ACS-010 | Wiki Composition | FRS-010 | Generated notes include all mandatory body sections. |
| ACS-011 | Related Notes | FRS-011 | Related links are generated for notes sharing sub-category context. |
| ACS-012 | Provenance | FRS-012, NFRS-003 | Each note includes source trace metadata fields. |
| ACS-013 | Backup | FRS-013 | Existing wiki files are backed up before overwrite. |
| ACS-014 | Reviewed Protection | FRS-014 | Notes marked reviewed are skipped and logged. |
| ACS-015 | Status Control | FRS-015 | Output notes contain valid status values from approved set. |
| ACS-016 | Determinism | FRS-016, NFRS-001 | Two identical runs produce equivalent folder structure and chunk boundaries. |
| ACS-017 | Error Isolation | FRS-017, NFRS-004 | Per-note failures do not terminate the full processing run. |
| ACS-018 | Logging | FRS-018 | Structured logs contain processed, skipped, failed, and chunking decisions. |
| ACS-019 | Idempotency | NFRS-002 | Rerun does not duplicate note files or chunk IDs. |
| ACS-020 | Maintainability | NFRS-005 | Keyword and chunking thresholds are configurable without code edits. |
| ACS-021 | Performance | NFRS-006 | Throughput remains within expected range for baseline dataset size. |

## 12. Test Strategy
- Unit tests:
  - frontmatter parsing fallbacks
  - keyword selection and exclusion
  - chunk boundary and merge logic
  - path generation and slug normalization
- Integration tests:
  - raw-to-wiki conversion end-to-end
  - reviewed skip behavior
  - backup + overwrite behavior
  - deterministic rerun validation
- Regression tests:
  - sample category corpus output snapshots
  - chunk boundary stability checks

## 13. Definition of Done
Release is accepted only when:
- FRS-001 to FRS-018 are implemented.
- NFRS-001 to NFRS-006 are validated.
- ACS-001 to ACS-021 pass.
- No open High severity defects.
- Operational runbook exists for skip/failure recovery.
