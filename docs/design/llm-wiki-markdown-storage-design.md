# Design: Storing Extracted Page Data as Markdown Files


## Related Documents
- [LLM Wiki Crawler Design](llm-wiki-crawler-design.md)
- [LLM Wiki Crawler Requirements](../requirements/llm-wiki-crawler-requirements-spec.md)
- [LLM Wiki Structure Config Requirements](../requirements/llm-wiki-structure-config-requirements-spec.md)
- [Wiki LLM Implementation Spec](wiki-llm-implementation-spec.md)
- [Wiki LLM Acceptance Criteria](wiki-llm-acceptance-criteria.md)

Implementation companion:
- See [Wiki LLM Implementation Spec](wiki-llm-implementation-spec.md) for build-level requirements.
- See [Wiki LLM Acceptance Criteria](wiki-llm-acceptance-criteria.md) for Definition of Done gates.

## Objective
Efficiently store the extracted content from each crawled internal page as a Markdown file, preserving metadata and ensuring traceability.

## Approach
- For every unique internal URL crawled:
  1. Extract the main content and metadata.
  2. Generate a unique, human-readable file path for the Markdown file, mirroring the website structure where possible.
  3. Write the content to a Markdown file with YAML frontmatter.

## Algorithm
1. **URL Normalization:**
   - Convert the URL path to a folder/file structure under the `raw/` directory.
   - Example: `https://www.ohsers.org/members/new-to-sers/benefits/` → `raw/members/new-to-sers/benefits.md`
   - If the URL does not end with a slash, use the last segment as the filename.
   - If the URL is not easily mapped, use a hash of the URL as the filename and store the original URL in the frontmatter.

2. **File Writing:**
   - For each page:
     - Build YAML frontmatter with fields like `title`, `source_url`, `source_domain`, `last_crawled`, `tags`, etc.
     - Write the extracted content as the Markdown body.
     - Save to the generated file path.

3. **Deduplication:**
   - Before writing, check if the file already exists.
   - If it exists, compare content hashes to avoid unnecessary overwrites.
   - Optionally, keep a log of all processed URLs and their output paths.

## Pseudocode
```python
for url in all_crawled_urls:
    content, metadata = extract_content_and_metadata(url)
    file_path = url_to_markdown_path(url)
    if not file_exists_or_changed(file_path, content):
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(build_frontmatter(metadata))
            f.write('\n\n')
            f.write(content)
```

## Benefits
- Each page is stored as a separate, traceable Markdown file.
- The structure is human-readable and easy to navigate in tools like Obsidian.
- Metadata is preserved for future processing, search, and provenance.

## Requirements
- Python 3.x
- Libraries: requests, BeautifulSoup, markdownify, PyYAML
- Consistent file/folder naming conventions
- Output: Markdown files with YAML frontmatter for each crawled page

## Handling Linked Documents

When recursively parsing URLs, only PDF links should be downloaded and converted.

1. **Detect Document Links:**
   - Check if the link points to a file.
   - If extension is `.pdf`, process it.
   - If extension is not `.pdf`, skip download and write a structured log entry with link details.

2. **Download Document:**
   - Download PDF files to a designated `docs/` or `attachments/` folder, preserving the original filename where possible.
   - Store the download path and original URL in metadata or in the YAML frontmatter of the referencing Markdown file.

3. **Reference in Markdown:**
   - In the Markdown file for the page containing the document link, add a reference to the downloaded document (e.g., `[Document: Member Disability Guide](../attachments/Member-Disability-Guide.pdf)`).

4. **Deduplication:**
   - Before downloading, check if the PDF has already been downloaded (by URL or filename).

5. **Unsupported Format Handling:**
   - Skip non-PDF documents.
   - Log at `warning` level with fields like `link_url`, `parent_url`, `extension`, `reason=unsupported_document_type`, `action=skipped`.

## Example Pseudocode
```python
for link in extract_links(html):
   if is_pdf_link(link):
      if not already_downloaded(link):
         download_document(link, save_path)
      add_reference_to_markdown(md_file, link, save_path)
   elif is_document_link(link):
      log_warning("unsupported_document_type", {
         "link_url": link,
         "parent_url": current_url,
         "extension": get_extension(link),
         "action": "skipped"
      })
    elif is_internal_link(link):
        # continue recursive crawl
```

## Benefits
- Ensures all referenced documents are archived locally.
- Maintains traceability between Markdown notes and original documents.
- Supports offline and reproducible LLM Wiki pipelines.

## Crawler Logging Design (Recommended)

Use structured JSON logging with event-based records so crawler behavior is auditable and easy to debug.

### Logging Algorithm
1. Emit one log event per significant action.
2. Include a `crawl_id` and `url` on every event for traceability.
3. Log start and end of each URL processing cycle.
4. Log discovered links count and classification counts (internal, external, pdf, skipped).
5. Log retries, failures, and final status.
6. For unsupported document types, log and skip.

### Required Log Fields
- `timestamp`
- `level` (`info`, `warning`, `error`)
- `event` (for example: `url_fetch_started`, `url_fetch_succeeded`, `url_saved_markdown`, `pdf_downloaded`, `pdf_converted`, `unsupported_document_skipped`, `external_link_skipped`, `url_failed`)
- `crawl_id`
- `url`
- `parent_url` (if applicable)
- `depth`
- `status`
- `message`
- `details` (dictionary for extra structured context)

### Log Levels
- `info`: Normal progress, counts, successful downloads/conversions.
- `warning`: Recoverable issues, skipped unsupported formats, timeout retries.
- `error`: Failed fetch/conversion after retries.

### Pseudocode
```python
log_info("url_fetch_started", {"url": url, "depth": depth, "crawl_id": crawl_id})

try:
   html = fetch(url)
   log_info("url_fetch_succeeded", {"url": url, "crawl_id": crawl_id})

   for link in extract_links(html):
      if is_pdf_link(link):
         path = download_pdf(link)
         log_info("pdf_downloaded", {"url": link, "parent_url": url, "path": path})
      elif is_document_link(link):
         log_warning("unsupported_document_skipped", {
            "url": link,
            "parent_url": url,
            "extension": get_extension(link),
            "reason": "unsupported_document_type"
         })
      elif is_external_link(link):
         log_info("external_link_skipped", {"url": link, "parent_url": url})

   log_info("url_processing_completed", {"url": url, "crawl_id": crawl_id})

except Exception as err:
   log_error("url_failed", {"url": url, "crawl_id": crawl_id, "error": str(err)})
```

### Log Outputs
- Write machine-readable logs to a file such as `crawler/logs/crawl-YYYYMMDD.jsonl`.
- Optionally print concise progress logs to console.
- Keep one JSON object per line for easy parsing and monitoring.

## YouTube Raw Transcript Extraction

When the crawler discovers a YouTube link, process it using a strict raw-transcript pipeline.

### Objective
- Extract raw transcript segments from YouTube.
- Preserve timestamps and segment boundaries.
- Store immutable raw outputs for downstream processing.

### Input and Output
- Input: `discovered_url`
- Output files:
   - `metadata.json`
   - `raw_segments.jsonl`
   - `status.json`
   - `errors.jsonl` (only when needed)

### Processing Algorithm
1. Normalize discovered URL.
2. Validate YouTube domain and URL format.
3. Extract `video_id`.
4. If raw transcript already exists for this `video_id`, skip reprocessing.
5. Set status to `processing`.
6. Fetch and save video metadata.
7. Try manual captions first.
8. If manual captions are unavailable, try auto captions.
9. If both caption methods fail, set status to `whisper_required`, download audio, transcribe with Whisper, and delete temporary audio.
10. Normalize transcript segments.
11. Write normalized segments as JSONL, one segment per line.
12. Set status to `raw_saved`.
13. On failure, log error and set status to `failed`.

### Segment Normalization Schema
Each segment must be normalized with this shape:

```json
{
   "id": "<video_id>_seg_<zero_padded_index>",
   "video_id": "<video_id>",
   "source_url": "<normalized_youtube_url>",
   "start": 12.34,
   "end": 18.90,
   "text": "<cleaned_text>",
   "language": "<detected_language>",
   "method": "youtube_manual_caption|youtube_auto_caption|whisper"
}
```

### Status Flow
- `discovered`
- `processing`
- `whisper_required`
- `raw_saved`
- `failed`

### Storage Structure
Store files under a per-video folder:

```text
/storage/youtube/{video_id}/
      metadata.json
      raw_segments.jsonl
      status.json
      errors.jsonl
```

### Required Functions
- `normalize_url(url)`
- `is_youtube_url(url)`
- `extract_video_id(url)`
- `fetch_video_metadata(url)`
- `fetch_manual_captions(video_id)`
- `fetch_auto_captions(video_id)`
- `download_audio(url)`
- `whisper_transcribe(audio_file)`
- `write_jsonl(rows, path)`
- `save_json(data, path)`
- `update_status(video_id, status)`
- `log_error(video_id, error)`

### Non-Negotiable Rules
1. Raw transcript must be immutable.
2. Preserve timestamps.
3. One segment per JSONL line.
4. Do not chunk.
5. Do not summarize.
6. Do not embed.
7. Whisper is fallback only.
8. Delete temporary audio after transcription.

## PDF Conversion to Markdown

When a linked document is a PDF:

1. **Download the PDF:**
   - Save the PDF to a designated folder (e.g., `attachments/` or `pdfs/`).

2. **Convert PDF to Markdown:**
   - Use a PDF-to-Markdown conversion tool or library (e.g., `pdfminer.six`, `PyMuPDF`, or external tools like `pandoc`).
   - Extract text and structure from the PDF and format it as Markdown.
   - Include the original PDF's metadata (title, source URL, download date) in the YAML frontmatter.

3. **Store as Markdown File:**
   - Save the converted Markdown file in the appropriate location (e.g., under `raw/` or `docs/`).
   - Reference the original PDF in the Markdown frontmatter or body for traceability.

4. **Reference in Other Notes:**
   - When a page links to the PDF, reference the converted Markdown file instead of (or in addition to) the original PDF.

## Example Pseudocode
```python
if is_pdf_link(link):
    pdf_path = download_pdf(link)
    md_content = convert_pdf_to_markdown(pdf_path)
    md_file_path = pdf_to_markdown_path(link)
    save_markdown(md_file_path, md_content, metadata)
    add_reference_to_markdown(parent_md_file, md_file_path)
```

## Benefits
- All content (including from PDFs) is searchable and usable by the LLM pipeline.
- Maintains provenance by linking back to the original PDF.
- Enables full-text analysis and downstream processing.

## Practical Systems Design Guardrails
Apply these principles to storage and transformation decisions:

1. Keep pipeline simple and deterministic.
2. Invest heavily in data quality and evaluation loops.
3. Add complexity only when metrics prove it is needed.

### Storage Decision Policy
- Default to deterministic schemas and immutable raw artifacts.
- Add new storage layers only when existing layers fail measurable quality/SLO targets.
- Every new transformation step must include:
   - explicit objective,
   - measurable success criteria,
   - rollback path.

### Core Quality and Eval Signals
- Metadata completeness rate
- Schema validation pass rate
- Markdown conversion fidelity
- Provenance coverage rate
- End-to-end retrieval usefulness from stored artifacts

---
**This design ensures that all crawled data is organized, deduplicated, and ready for downstream LLM Wiki processing.**
