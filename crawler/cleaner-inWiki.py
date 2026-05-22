import json
import re
import shutil
from pathlib import Path
from datetime import datetime, timezone

import yaml

FORCE_CLEAN_ALL = False
    
TAXONOMY_FILE = "taxonomy.json"
BACKUP_ROOT = Path("backups")


NOTE_RULES = {
    "retirement eligibility": {
        "include": [
            "service retirement eligibility",
            "eligibility requirements",
            "eligible",
            "eligibility",
            "unreduced",
            "age",
            "service credit",
            "retire"
        ],
        "exclude": [
            "calculating your own pension",
            "estimate",
            "apply",
            "application"
        ],
        "main_heading": "Eligibility Rules"
    },
    "early retirement": {
        "include": [
            "early service retirement",
            "early retirement",
            "reduced benefit",
            "reduced benefits",
            "reduction",
            "eligible"
        ],
        "exclude": [
            "calculating your own pension",
            "application",
            "estimate"
        ],
        "main_heading": "Early Retirement Rules"
    },
    "retirement process": {
        "include": [
            "apply",
            "application",
            "estimate",
            "retirement estimate",
            "account login",
            "steps toward retirement",
            "retirement date",
            "retiring from your sers-covered job"
        ],
        "exclude": [
            "calculating your own pension",
            "formula"
        ],
        "main_heading": "Process Details"
    },
    "benefit calculation": {
        "include": [
            "age + service credit + salary = pension",
            "calculating your own pension",
            "calculation",
            "calculate",
            "formula",
            "final average salary",
            "service credit",
            "salary",
            "pension"
        ],
        "exclude": [
            "application",
            "apply"
        ],
        "main_heading": "Calculation Details"
    },
    "retirement": {
        "include": [
            "when can you retire",
            "retirement basics",
            "retirement",
            "plan for retirement"
        ],
        "exclude": [],
        "main_heading": "Overview"
    }
}


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
        print(f"Invalid JSON found in {path}. Using default value.")
        return default


def read_text(path):
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        file.write(text)


def parse_frontmatter(markdown_text):
    pattern = r"(?s)^---\s*\n(.*?)\n---\s*\n?(.*)$"
    match = re.match(pattern, markdown_text)

    if not match:
        return {}, markdown_text

    yaml_text = match.group(1)
    body = match.group(2)

    try:
        metadata = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError:
        metadata = {}

    return metadata, body


def get_section(body, heading):
    """
    Extracts section like:
    ## Full Crawled Source Content
    """

    pattern = rf"(?is)^##\s+{re.escape(heading)}\s*\n(.*?)(?=\n---|\n##\s+|\Z)"
    match = re.search(pattern, body, flags=re.MULTILINE)

    if match:
        return match.group(1).strip()

    return ""


def normalize_title(text):
    return re.sub(r"\s+", " ", text.strip().lower())


def word_count(text):
    return len(re.findall(r"\b\w+\b", text))


def remove_website_navigation(content):
    """
    Removes top menu/navigation content before actual article starts.
    """

    useful_start_patterns = [
        r"#+\s*When Can You Retire\?",
        r"#+\s*Service Retirement Eligibility",
        r"#+\s*AGE\s*\+\s*SERVICE CREDIT\s*\+\s*SALARY\s*=\s*PENSION",
        r"#+\s*Calculating Your Own Pension",
        r"#+\s*Retirement Basics"
    ]

    for pattern in useful_start_patterns:
        match = re.search(pattern, content, flags=re.IGNORECASE)
        if match:
            return content[match.start():].strip()

    return content.strip()


def remove_noise_lines(content):
    noise_phrases = [
        "Skip to content",
        "Toggle search",
        "Search for:",
        "BACK TO WORKING MEMBERS",
        "BACK TO READY TO RETIRE",
        "Continue Reading",
        "Facebook",
        "LinkedIn",
        "CONTACT US",
        "SITEMAP",
        "This note contains cleaned information extracted",
        "This raw note was generated",
        "reviewed and cleaned before being promoted"
    ]

    cleaned_lines = []

    for line in content.splitlines():
        stripped = line.strip()

        if not stripped:
            continue

        if any(phrase.lower() in stripped.lower() for phrase in noise_phrases):
            continue

        # Remove menu-only markdown links like:
        # + [Membership](...)
        # * [Working Members](...)
        if re.match(r"^[*+\-]\s+\[.+?\]\(.+?\)\s*$", stripped):
            continue

        cleaned_lines.append(stripped)

    return "\n".join(cleaned_lines)


def normalize_spacing(content):
    lines = [line.rstrip() for line in content.splitlines()]
    result = []
    previous_blank = False

    for line in lines:
        if not line.strip():
            if not previous_blank:
                result.append("")
            previous_blank = True
        else:
            result.append(line.strip())
            previous_blank = False

    return "\n".join(result).strip()


def split_markdown_blocks(content):
    """
    Splits markdown into heading blocks.
    Each block starts with a markdown heading if available.
    """

    parts = re.split(r"(?m)(?=^#{1,6}\s+)", content)
    blocks = []

    for part in parts:
        cleaned = part.strip()
        if cleaned:
            blocks.append(cleaned)

    return blocks


def score_block(block, include_keywords, exclude_keywords):
    lower_block = block.lower()

    score = 0

    for keyword in include_keywords:
        if keyword.lower() in lower_block:
            score += 2

    for keyword in exclude_keywords:
        if keyword.lower() in lower_block:
            score -= 2

    return score


def extract_relevant_content(content, item):
    title_key = normalize_title(item.get("title", ""))
    topic_key = normalize_title(item.get("topic", ""))

    rule = NOTE_RULES.get(title_key)

    if rule is None:
        rule = NOTE_RULES.get(topic_key, {
            "include": item.get("section_keywords", []),
            "exclude": [],
            "main_heading": "Extracted Content"
        })

    include_keywords = rule.get("include", []) + item.get("section_keywords", [])
    exclude_keywords = rule.get("exclude", [])

    content = remove_website_navigation(content)
    content = remove_noise_lines(content)
    content = normalize_spacing(content)

    blocks = split_markdown_blocks(content)

    selected_blocks = []

    for block in blocks:
        score = score_block(block, include_keywords, exclude_keywords)

        if score > 0:
            selected_blocks.append(block)

    # Remove duplicate blocks while keeping order
    unique_blocks = []
    seen = set()

    for block in selected_blocks:
        key = re.sub(r"\s+", " ", block.lower()).strip()

        if key not in seen:
            seen.add(key)
            unique_blocks.append(block)

    extracted = "\n\n".join(unique_blocks).strip()

    # Fallback if matching was too weak
    if word_count(extracted) < 60:
        extracted = content

    return normalize_spacing(extracted), rule.get("main_heading", "Extracted Content")


def build_related_notes(current_item, all_items):
    current_output = current_item.get("output_path")
    current_sub_category = current_item.get("sub_category")

    related = []

    for item in all_items:
        if item.get("output_path") == current_output:
            continue

        if item.get("sub_category") == current_sub_category:
            note_name = Path(item["output_path"]).stem
            related.append(note_name)

    return related


def build_frontmatter(item, raw_metadata, related_notes, confidence):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    metadata = {
        "title": item.get("title", raw_metadata.get("title", "")),
        "main_category": item.get("main_category", raw_metadata.get("main_category", "")),
        "sub_category": item.get("sub_category", raw_metadata.get("sub_category", "")),
        "topic": item.get("topic", raw_metadata.get("topic", "")),
        "audience": raw_metadata.get("audience", "active_member"),
        "content_type": item.get("content_type", raw_metadata.get("content_type", "guide")),
        "source_url": item.get("url", raw_metadata.get("source_url", "")),
        "source_hash": raw_metadata.get("source_hash", ""),
        "last_cleaned": today,
        "status": "auto_cleaned",
        "cleaning_confidence": confidence,
        "tags": item.get("tags", raw_metadata.get("tags", [])),
        "related_notes": related_notes
    }

    return "---\n" + yaml.safe_dump(
        metadata,
        sort_keys=False,
        allow_unicode=True
    ) + "---\n\n"


def build_body(item, main_heading, extracted_content, related_notes):
    title = item["title"]
    source_url = item["url"]

    related_links = "\n".join([f"- [[{note}]]" for note in related_notes])

    if not related_links:
        related_links = "- No related notes added yet."

    body = f"""# {title}

## Overview

This note contains topic-specific information extracted from the official OHSERS source.

## {main_heading}

{extracted_content}

## Related Notes

{related_links}

## Source

- {source_url}
"""

    return body.strip() + "\n"


def is_reviewed_file(path):
    if not path.exists():
        return False

    if path.stat().st_size == 0:
        return False

    text = read_text(path)
    metadata, _ = parse_frontmatter(text)

    return metadata.get("status") == "reviewed"


def backup_file(file_path, vault_path):
    if not file_path.exists():
        return

    if file_path.stat().st_size == 0:
        return

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    try:
        relative_path = file_path.relative_to(vault_path)
    except ValueError:
        relative_path = Path(file_path.name)

    backup_path = BACKUP_ROOT / timestamp / relative_path
    backup_path.parent.mkdir(parents=True, exist_ok=True)

    shutil.copy2(file_path, backup_path)


def calculate_confidence(extracted_content):
    count = word_count(extracted_content)

    if count >= 200:
        return "high"

    if count >= 80:
        return "medium"

    return "low"


def clean_raw_to_wiki():
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
        raw_relative = item["output_path"]
        wiki_relative = raw_relative.replace("raw/", "wiki/", 1)

        raw_path = vault_path / raw_relative
        wiki_path = vault_path / wiki_relative

        print(f"\nProcessing: {item['title']}")
        print(f"Raw : {raw_path}")
        print(f"Wiki: {wiki_path}")

        try:
            if not raw_path.exists():
                print("Skipped: raw file not found.")
                skipped.append(str(raw_path))
                continue

            if is_reviewed_file(wiki_path):
                print("Skipped: wiki file already reviewed.")
                skipped.append(str(wiki_path))
                continue

            raw_text = read_text(raw_path)

            if not raw_text.strip():
                print("Skipped: raw file is empty.")
                skipped.append(str(raw_path))
                continue

            raw_metadata, raw_body = parse_frontmatter(raw_text)

            full_content = get_section(raw_body, "Full Crawled Source Content")

            if not full_content:
                full_content = get_section(raw_body, "Extracted Content")

            if not full_content:
                full_content = raw_body

            extracted_content, main_heading = extract_relevant_content(full_content, item)
            confidence = calculate_confidence(extracted_content)
            related_notes = build_related_notes(item, items)

            frontmatter = build_frontmatter(
                item=item,
                raw_metadata=raw_metadata,
                related_notes=related_notes,
                confidence=confidence
            )

            body = build_body(
                item=item,
                main_heading=main_heading,
                extracted_content=extracted_content,
                related_notes=related_notes
            )

            final_markdown = frontmatter + body

            backup_file(wiki_path, vault_path)
            write_text(wiki_path, final_markdown)

            print(f"Updated: {wiki_path}")
            print(f"Confidence: {confidence}")
            converted.append(str(wiki_path))

        except Exception as error:
            print(f"Failed: {error}")
            failed.append({
                "title": item.get("title", "unknown"),
                "error": str(error)
            })

    print("\n========== SMART CLEANING SUMMARY ==========")
    print(f"Converted/Updated: {len(converted)}")
    print(f"Skipped: {len(skipped)}")
    print(f"Failed: {len(failed)}")

    if converted:
        print("\nUpdated files:")
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
    clean_raw_to_wiki()