# LLM Wiki Crawler Design Document

Implementation companion:
- See wiki-llm-implementation-spec.md for build-level requirements.
- See wiki-llm-acceptance-criteria.md for Definition of Done gates.

## Objective
Design a robust crawler for the LLM Wiki that:
- Extracts raw data from a given set of seed URLs.
- Recursively discovers and downloads all internal links (deep links) within the same domain.
- Avoids downloading external links.
- Maintains a deduplicated list of all visited and queued URLs.
- Stops when no new internal links remain.
- Processes discovered document links with strict rules:
   - PDF: download and convert to Markdown.
   - Non-PDF files: skip and log structured warning.
- Processes discovered YouTube links through raw transcript extraction workflow.

## Algorithm Overview
- **Approach:** Breadth-First Search (BFS) crawler with deduplication and domain filtering.
- **Data Structures:**
   - `queue`: URLs to visit (FIFO, use deque).
   - `seen`: Canonical URLs already visited or queued.
   - `failed`: URLs that failed after retries.
   - `state`: Persistent crawl checkpoint (queue/seen/failed/counters).

## Mandatory Crawl Controls
- `max_depth`: hard limit for recursion depth.
- `max_pages`: hard limit for total processed pages.
- `allowed_paths`: optional allowlist (recommended for site sections such as /members/).
- `request_timeout_seconds`: fetch timeout.
- `max_retries`: retry attempts for transient failures.
- `backoff_seconds`: exponential backoff base.

## URL Canonicalization Rules
Apply before deduplication and queueing:
- Lowercase scheme and host.
- Remove URL fragment.
- Normalize trailing slash policy.
- Remove known tracking query params.
- Resolve relative URLs against parent URL.
- Reject unsupported schemes (only http/https).

## Steps
1. **Initialization:**
   - Start with a list of seed URLs (from taxonomy or config).
    - Canonicalize each URL.
    - Add each canonical URL to `queue` and `seen`.
    - Persist initial state.

2. **Crawling Loop:**
   - While `queue` is not empty:
       - Pop the next URL from `queue`.
       - Skip if depth or page limits are reached.
       - Download and parse the page with retries and backoff.
     - Extract main content and save as a raw Markdown note.
     - Extract all internal links from the page.
     - For each internal link:
          - Canonicalize link.
          - If link is YouTube, send to YouTube raw transcript pipeline.
          - If link is document:
             - If PDF: download and convert to Markdown.
             - Else: skip and log warning with link details.
          - If eligible internal HTML link and not in `seen`, add to `queue` and `seen`.
     - Ignore external links (different domain).
       - Persist checkpoint state periodically.

3. **Deduplication:**
    - Only process each canonical URL once (using `seen`).

4. **Domain Filtering:**
   - Only follow links that match the target domain or a whitelist pattern.

5. **Termination:**
   - Stop when `queue` is empty (all reachable internal pages have been crawled).

6. **Failure Handling:**
    - If fetch/parse/save fails after retries, record URL in `failed` and log error.
    - Continue crawl for remaining URLs.

7. **Resume Support:**
    - On restart, load checkpointed state and continue from saved queue.

## Pseudocode
```python
from collections import deque

queue = deque(canonicalize(seed) for seed in seed_urls)
seen = set(queue)
failed = set()

while queue:
      url = queue.popleft()
      if limits_reached():
            break

      try:
            html = fetch_with_retry(url)
            save_markdown(html, url)

            for link in extract_links(html, parent_url=url):
                  normalized = canonicalize(link)

                  if is_youtube_url(normalized):
                        process_youtube_raw_transcript(normalized)
                        continue

                  if is_document_link(normalized):
                        if is_pdf_link(normalized):
                              pdf_path = download_pdf(normalized)
                              save_pdf_as_markdown(pdf_path, normalized)
                        else:
                              log_warning("unsupported_document_skipped", {
                                    "link_url": normalized,
                                    "parent_url": url,
                                    "extension": file_extension(normalized),
                                    "reason": "unsupported_document_type",
                                    "action": "skipped"
                              })
                        continue

                  if is_internal_html_link(normalized, domain) and normalized not in seen:
                        seen.add(normalized)
                        queue.append(normalized)

            checkpoint_state(queue, seen, failed)

      except Exception as err:
            failed.add(url)
            log_error("url_failed", {"url": url, "error": str(err)})
```

## Key Functions
- `fetch(url)`: Download HTML content.
- `extract_internal_links(html, domain)`: Return all internal links from the HTML.
- `save_markdown(html, url)`: Extract main content and save as Markdown with metadata.
- `canonicalize(url)`: Normalize URL before dedupe/queue.
- `fetch_with_retry(url)`: Retry with exponential backoff.
- `checkpoint_state(...)`: Persist queue/seen/failed for resume.
- `process_youtube_raw_transcript(url)`: Handle YouTube links via transcript extraction pipeline.
- `download_pdf(url)`: Download PDF document.
- `save_pdf_as_markdown(pdf_path, source_url)`: Convert PDF to Markdown and save.
- `log_warning(event, details)`: Structured warning log.
- `log_error(event, details)`: Structured error log.

## Requirements
- Python 3.x
- Libraries: requests, BeautifulSoup, markdownify, PyYAML
- Configurable seed URLs and domain filter.
- Structured JSONL logging.
- Persistent state/checkpointing for resume.
- PDF-to-Markdown conversion support.
- Output: Raw Markdown notes for each crawled page, with YAML frontmatter.

## Logging Requirements
Log one structured JSON event per significant action.

Required fields:
- `timestamp`
- `level` (`info`, `warning`, `error`)
- `event`
- `crawl_id`
- `url`
- `parent_url` (when applicable)
- `depth`
- `status`
- `message`
- `details`

Recommended events:
- `url_fetch_started`
- `url_fetch_succeeded`
- `url_saved_markdown`
- `external_link_skipped`
- `pdf_downloaded`
- `pdf_converted_to_markdown`
- `unsupported_document_skipped`
- `youtube_discovered`
- `url_failed`
- `crawl_checkpoint_saved`

## Notes
- Store parent-child relationships for traceability where possible.
- Raw transcript and raw markdown artifacts should be immutable after write.
- Whisper is fallback only for YouTube transcript extraction.

## Practical Systems Design Guardrails
Use these guardrails for all crawler changes:

1. Keep pipeline simple and deterministic.
2. Invest heavily in data quality and evaluation loops.
3. Add complexity only when metrics prove it is needed.

### Implementation Policy
- Prefer deterministic rules over heuristic branching unless validated by metrics.
- Any new component must define:
      - expected quality gain,
      - measurement plan,
      - rollback criteria.
- If a simpler approach meets SLO and quality targets, keep the simpler approach.

### Minimum Metrics Before Adding Complexity
- Crawl success rate
- Parse success rate
- Duplicate rate
- Freshness lag
- Citation/source-trace accuracy
- Abstain correctness (for answering layer)

---
**This design ensures comprehensive, deduplicated, and domain-specific crawling for LLM Wiki ingestion.**
