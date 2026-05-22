import json
import hashlib
import time
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
import yaml
from bs4 import BeautifulSoup
from markdownify import markdownify as md


TAXONOMY_FILE = "taxonomy.json"
STATE_FILE = "state.json"

HEADERS = {
    "User-Agent": "OHSERS-Obsidian-Student-Crawler/1.0"
}


def load_json(path, default):
    file_path = Path(path)

    if not file_path.exists():
        return default

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def normalize_text(text):
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def get_hash(text):
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def fetch_html(url):
    response = requests.get(url, headers=HEADERS, timeout=25)
    response.raise_for_status()
    return response.text


def extract_main_content(html):
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "noscript", "svg", "form"]):
        tag.decompose()

    candidates = [
        "main",
        "article",
        ".entry-content",
        ".post-content",
        ".page-content",
        "#content"
    ]

    selected = None

    for selector in candidates:
        found = soup.select_one(selector)
        if found and len(found.get_text(strip=True)) > 500:
            selected = found
            break

    if selected is None:
        selected = soup.body or soup

    for selector in [
        "nav",
        "footer",
        "header",
        ".menu",
        ".sidebar",
        ".search",
        ".breadcrumb",
        ".navigation"
    ]:
        for tag in selected.select(selector):
            tag.decompose()

    markdown = md(str(selected), heading_style="ATX")
    return cleanup_markdown(markdown)


def cleanup_markdown(markdown):
    lines = markdown.splitlines()
    cleaned = []

    skip_phrases = [
        "Skip to content",
        "Toggle search",
        "Search for:",
        "BACK TO WORKING MEMBERS",
        "Continue Reading",
        "Facebook",
        "LinkedIn",
        "CONTACT US",
        "SITEMAP"
    ]

    for line in lines:
        stripped = line.strip()

        if not stripped:
            continue

        if any(phrase.lower() in stripped.lower() for phrase in skip_phrases):
            continue

        cleaned.append(stripped)

    return "\n\n".join(cleaned)


def keyword_score(text, keywords):
    text_lower = text.lower()
    score = 0

    for keyword in keywords:
        if keyword.lower() in text_lower:
            score += 1

    return score


def extract_relevant_content(full_content, item):
    """
    Version 1 approach:
    - Page content is extracted once.
    - For every note, we keep the full official source content,
      but add a 'Relevant Focus' section based on keywords.
    - This avoids missing important data in the first version.
    """

    keywords = item.get("section_keywords", [])
    lines = full_content.split("\n\n")

    relevant_lines = []

    for line in lines:
        if keyword_score(line, keywords) > 0:
            relevant_lines.append(line)

    if relevant_lines:
        relevant = "\n\n".join(relevant_lines)
    else:
        relevant = "No focused section was confidently extracted. Review the full crawled content below."

    return relevant


def build_frontmatter(item, source_hash):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    frontmatter = {
        "title": item["title"],
        "main_category": item["main_category"],
        "sub_category": item["sub_category"],
        "topic": item["topic"],
        "audience": "active_member",
        "content_type": item["content_type"],
        "source_url": item["url"],
        "source_domain": urlparse(item["url"]).netloc,
        "source_hash": source_hash,
        "last_crawled": today,
        "tags": item.get("tags", []),
        "status": "raw_crawled"
    }

    return "---\n" + yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True) + "---\n\n"


def build_markdown_note(item, full_content, source_hash):
    frontmatter = build_frontmatter(item, source_hash)
    relevant_content = extract_relevant_content(full_content, item)

    body = f"""# {item["title"]}

## Note Purpose

This raw note was generated from the official SERS source page. It should be reviewed and cleaned before being promoted to the wiki folder.

## Relevant Focus

{relevant_content}

---

## Full Crawled Source Content

{full_content}

---

## Source

- {item["url"]}
"""

    return frontmatter + body


def write_markdown(vault_path, output_path, markdown):
    full_path = Path(vault_path) / output_path
    full_path.parent.mkdir(parents=True, exist_ok=True)

    with open(full_path, "w", encoding="utf-8") as file:
        file.write(markdown)

    return full_path


def crawl():
    taxonomy = load_json(TAXONOMY_FILE, {})
    state = load_json(STATE_FILE, {})

    if "vault_path" not in taxonomy:
        raise ValueError("taxonomy.json me vault_path missing hai.")

    if "items" not in taxonomy:
        raise ValueError("taxonomy.json me items missing hai.")

    vault_path = taxonomy["vault_path"]
    items = taxonomy["items"]

    changed_files = []
    unchanged_files = []
    failed_items = []

    content_cache = {}

    for item in items:
        title = item["title"]
        url = item["url"]
        output_path = item["output_path"]

        print(f"\nCrawling: {title}")
        print(f"URL: {url}")

        try:
            if url not in content_cache:
                html = fetch_html(url)
                full_content = extract_main_content(html)
                content_cache[url] = full_content
                time.sleep(2)
            else:
                full_content = content_cache[url]

            source_hash = get_hash(full_content)
            state_key = output_path

            old_hash = state.get(state_key, {}).get("source_hash")

            if old_hash == source_hash:
                print("No change detected.")
                unchanged_files.append(output_path)
            else:
                print("Change detected or empty file found. Updating markdown file.")

                markdown = build_markdown_note(item, full_content, source_hash)
                saved_path = write_markdown(vault_path, output_path, markdown)

                state[state_key] = {
                    "source_url": url,
                    "source_hash": source_hash,
                    "last_crawled": datetime.now(timezone.utc).isoformat(),
                    "last_output_path": output_path
                }

                changed_files.append(str(saved_path))

        except Exception as error:
            print(f"Failed: {title} -> {error}")
            failed_items.append({
                "title": title,
                "url": url,
                "error": str(error)
            })

    save_json(STATE_FILE, state)

    print("\n========== SUMMARY ==========")
    print(f"Changed files: {len(changed_files)}")
    print(f"Unchanged files: {len(unchanged_files)}")
    print(f"Failed items: {len(failed_items)}")

    if changed_files:
        print("\nUpdated files:")
        for file in changed_files:
            print(f"- {file}")

    if failed_items:
        print("\nFailed items:")
        for item in failed_items:
            print(f"- {item['title']}: {item['error']}")


if __name__ == "__main__":
    crawl()