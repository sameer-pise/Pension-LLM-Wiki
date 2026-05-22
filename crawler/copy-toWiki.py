import json
import re
import shutil
from pathlib import Path
from datetime import datetime, timezone

import yaml


TAXONOMY_FILE = "taxonomy.json"
BACKUP_DIR = Path("backups")


def load_json(path, default):
    file_path = Path(path)

    if not file_path.exists():
        return default

    if file_path.stat().st_size == 0:
        return default

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        print(f"Warning: {path} is invalid JSON. Using default value.")
        return default


def read_text(path):
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        file.write(text)


def parse_frontmatter(markdown_text):
    """
    Returns:
    metadata dict, body text
    """

    if not markdown_text.startswith("---"):
        return {}, markdown_text

    parts = markdown_text.split("---", 2)

    if len(parts) < 3:
        return {}, markdown_text

    yaml_text = parts[1]
    body_text = parts[2].strip()

    try:
        metadata = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError:
        metadata = {}

    return metadata, body_text


def extract_section(markdown_text, heading_name):
    """
    Extracts content under a level-2 heading like:
    ## Relevant Focus
    """

    pattern = rf"(?is)^##\s+{re.escape(heading_name)}\s*\n(.*?)(?=\n---|\n##\s+|\Z)"
    match = re.search(pattern, markdown_text, flags=re.MULTILINE)

    if not match:
        return ""

    return match.group(1).strip()


def normalize_whitespace(text):
    lines = text.splitlines()
    cleaned_lines = []

    previous_line = None

    for line in lines:
        stripped = line.strip()

        if not stripped:
            continue

        # avoid exact repeated lines
        if stripped == previous_line:
            continue

        cleaned_lines.append(stripped)
        previous_line = stripped

    return "\n\n".join(cleaned_lines)


def remove_noise(text):
    noise_phrases = [
        "Raw Crawled Content",
        "Full Crawled Source Content",
        "Note Purpose",
        "This raw note was generated",
        "reviewed and cleaned before being promoted",
        "Skip to content",
        "Toggle search",
        "Search for:",
        "BACK TO WORKING MEMBERS",
        "BACK TO READY TO RETIRE",
        "Continue Reading",
        "Facebook",
        "LinkedIn",
        "CONTACT US",
        "SITEMAP"
    ]

    lines = text.splitlines()
    result = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            continue

        if any(phrase.lower() in stripped.lower() for phrase in noise_phrases):
            continue

        result.append(stripped)

    return normalize_whitespace("\n".join(result))


def keyword_context(full_content, keywords, window=2):
    """
    Takes full crawled content and extracts blocks around keyword matches.
    This gives cleaner focused content for each note.
    """

    if not keywords:
        return ""

    blocks = [block.strip() for block in full_content.split("\n\n") if block.strip()]
    matched_indexes = set()

    for index, block in enumerate(blocks):
        lower_block = block.lower()

        for keyword in keywords:
            if keyword.lower() in lower_block:
                start = max(0, index - window)
                end = min(len(blocks), index + window + 1)

                for i in range(start, end):
                    matched_indexes.add(i)

    if not matched_indexes:
        return ""

    ordered_blocks = [blocks[i] for i in sorted(matched_indexes)]
    return "\n\n".join(ordered_blocks)


def word_count(text):
    return len(re.findall(r"\w+", text))


def build_related_notes(current_item, all_items):
    current_sub_category = current_item.get("sub_category")
    current_output = current_item.get("output_path")

    related = []

    for item in all_items:
        if item.get("output_path") == current_output:
            continue

        if item.get("sub_category") == current_sub_category:
            note_name = Path(item["output_path"]).stem
            related.append(note_name)

    return related


def build_clean_frontmatter(raw_metadata, item, related_notes):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    clean_metadata = {
        "title": item.get("title", raw_metadata.get("title", "")),
        "main_category": item.get("main_category", raw_metadata.get("main_category", "")),
        "sub_category": item.get("sub_category", raw_metadata.get("sub_category", "")),
        "topic": item.get("topic", raw_metadata.get("topic", "")),
        "audience": raw_metadata.get("audience", "active_member"),
        "content_type": item.get("content_type", raw_metadata.get("content_type", "")),
        "source_url": item.get("url", raw_metadata.get("source_url", "")),
        "source_hash": raw_metadata.get("source_hash", ""),
        "last_cleaned": today,
        "status": "clean_draft",
        "tags": item.get("tags", raw_metadata.get("tags", [])),
        "related_notes": related_notes
    }

    return "---\n" + yaml.safe_dump(
        clean_metadata,
        sort_keys=False,
        allow_unicode=True
    ) + "---\n\n"


def build_clean_body(item, cleaned_content, related_notes):
    title = item["title"]
    source_url = item["url"]

    related_links = "\n".join([f"- [[{note}]]" for note in related_notes])

    if not related_links:
        related_links = "- No related notes added yet."

    body = f"""# {title}

## Overview

This note contains cleaned information extracted from the official OHSERS source page.

## Extracted Content

{cleaned_content}

## Related Notes

{related_links}

## Source

- {source_url}
"""

    return body


def backup_existing_file(file_path, vault_path):
    if not file_path.exists():
        return

    if file_path.stat().st_size == 0:
        return

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    try:
        relative_path = file_path.relative_to(vault_path)
    except ValueError:
        relative_path = file_path.name

    backup_path = BACKUP_DIR / timestamp / relative_path
    backup_path.parent.mkdir(parents=True, exist_ok=True)

    shutil.copy2(file_path, backup_path)


def should_skip_existing_wiki_file(wiki_path):
    """
    If wiki note is already reviewed, do not overwrite it.
    """

    if not wiki_path.exists():
        return False

    text = read_text(wiki_path)
    metadata, _ = parse_frontmatter(text)

    return metadata.get("status") == "reviewed"


def convert_raw_to_wiki():
    taxonomy = load_json(TAXONOMY_FILE, {})

    if "vault_path" not in taxonomy:
        raise ValueError("taxonomy.json me vault_path missing hai.")

    if "items" not in taxonomy:
        raise ValueError("taxonomy.json me items missing hai.")

    vault_path = Path(taxonomy["vault_path"])
    items = taxonomy["items"]

    converted = []
    skipped = []
    failed = []

    for item in items:
        raw_relative_path = item["output_path"]
        wiki_relative_path = raw_relative_path.replace("raw/", "wiki/", 1)

        raw_path = vault_path / raw_relative_path
        wiki_path = vault_path / wiki_relative_path

        print(f"\nProcessing: {item['title']}")

        try:
            if not raw_path.exists():
                print(f"Raw file not found: {raw_path}")
                skipped.append(str(raw_path))
                continue

            if should_skip_existing_wiki_file(wiki_path):
                print("Skipped because wiki file is already reviewed.")
                skipped.append(str(wiki_path))
                continue

            raw_text = read_text(raw_path)
            raw_metadata, raw_body = parse_frontmatter(raw_text)

            full_content = extract_section(raw_body, "Full Crawled Source Content")
            relevant_focus = extract_section(raw_body, "Relevant Focus")

            if not full_content:
                full_content = raw_body

            keywords = item.get("section_keywords", [])
            focused_content = keyword_context(full_content, keywords, window=2)

            if word_count(focused_content) < 40:
                focused_content = relevant_focus

            if word_count(focused_content) < 40:
                focused_content = full_content

            cleaned_content = remove_noise(focused_content)

            related_notes = build_related_notes(item, items)

            frontmatter = build_clean_frontmatter(
                raw_metadata=raw_metadata,
                item=item,
                related_notes=related_notes
            )

            body = build_clean_body(
                item=item,
                cleaned_content=cleaned_content,
                related_notes=related_notes
            )

            final_markdown = frontmatter + body

            backup_existing_file(wiki_path, vault_path)
            write_text(wiki_path, final_markdown)

            print(f"Created/updated: {wiki_path}")
            converted.append(str(wiki_path))

        except Exception as error:
            print(f"Failed: {item['title']} -> {error}")
            failed.append({
                "title": item["title"],
                "error": str(error)
            })

    print("\n========== CLEANING SUMMARY ==========")
    print(f"Converted: {len(converted)}")
    print(f"Skipped: {len(skipped)}")
    print(f"Failed: {len(failed)}")

    if converted:
        print("\nConverted files:")
        for file in converted:
            print(f"- {file}")

    if skipped:
        print("\nSkipped files:")
        for file in skipped:
            print(f"- {file}")

    if failed:
        print("\nFailed:")
        for item in failed:
            print(f"- {item['title']}: {item['error']}")


if __name__ == "__main__":
    convert_raw_to_wiki()