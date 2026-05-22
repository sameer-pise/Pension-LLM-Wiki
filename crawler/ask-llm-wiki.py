import json
import re
import sys
from pathlib import Path

import requests
import yaml


TAXONOMY_FILE = "taxonomy.json"

# For now, only Retirement category
WIKI_RELATIVE_FOLDER = "wiki/member-benefits/retirement"

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3"


def load_json(path):
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"{path} not found.")

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def read_text(path):
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def parse_frontmatter(markdown_text):
    pattern = r"(?s)^---\s*\n(.*?)\n---\s*\n?(.*)$"
    match = re.match(pattern, markdown_text)

    if not match:
        return {}, markdown_text

    yaml_text = match.group(1)
    body = match.group(2).strip()

    try:
        metadata = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError:
        metadata = {}

    return metadata, body


def tokenize(text):
    text = text.lower()
    words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9\-]+\b", text)

    stopwords = {
        "what", "when", "where", "how", "why", "is", "are", "the", "a", "an",
        "of", "to", "for", "in", "on", "and", "or", "with", "does", "do",
        "can", "member", "members", "active", "tell", "me", "about"
    }

    return [word for word in words if word not in stopwords]


def load_wiki_notes(vault_path):
    wiki_path = Path(vault_path) / WIKI_RELATIVE_FOLDER

    if not wiki_path.exists():
        raise FileNotFoundError(f"Wiki folder not found: {wiki_path}")

    notes = []

    for md_file in sorted(wiki_path.glob("*.md")):
        text = read_text(md_file)

        if not text.strip():
            continue

        metadata, body = parse_frontmatter(text)

        notes.append({
            "file_name": md_file.name,
            "file_path": str(md_file),
            "title": metadata.get("title", md_file.stem),
            "topic": metadata.get("topic", ""),
            "content_type": metadata.get("content_type", ""),
            "tags": metadata.get("tags", []),
            "related_notes": metadata.get("related_notes", []),
            "source_url": metadata.get("source_url", ""),
            "body": body
        })

    if not notes:
        raise ValueError("No markdown notes found in wiki folder.")

    return notes


def note_search_text(note):
    tags = note.get("tags", [])
    if isinstance(tags, list):
        tags_text = " ".join(tags)
    else:
        tags_text = str(tags)

    related = note.get("related_notes", [])
    if isinstance(related, list):
        related_text = " ".join(related)
    else:
        related_text = str(related)

    return f"""
    {note.get("title", "")}
    {note.get("topic", "")}
    {note.get("content_type", "")}
    {tags_text}
    {related_text}
    {note.get("body", "")}
    """


def score_note(question, note):
    question_tokens = tokenize(question)
    search_text = note_search_text(note).lower()

    score = 0

    title = note.get("title", "").lower()
    topic = note.get("topic", "").lower()
    content_type = note.get("content_type", "").lower()

    for token in question_tokens:
        if token in title:
            score += 8
        if token in topic:
            score += 6
        if token in content_type:
            score += 4
        if token in search_text:
            score += 1

    # phrase boosts
    q = question.lower()

    if "eligibility" in q and "eligibility" in title:
        score += 20

    if "early retirement" in q and "early retirement" in title:
        score += 20

    if "calculate" in q or "calculation" in q or "pension" in q:
        if "calculation" in title or "benefit calculation" in title:
            score += 20

    if "process" in q or "apply" in q or "application" in q:
        if "process" in title:
            score += 20

    if "retire" in q or "retirement" in q:
        if "retirement" in title:
            score += 5

    return score


def retrieve_notes(question, notes, top_k=3):
    scored = []

    for note in notes:
        score = score_note(question, note)
        scored.append((score, note))

    scored.sort(key=lambda item: item[0], reverse=True)

    selected = [note for score, note in scored if score > 0][:top_k]

    if not selected:
        selected = [scored[0][1]]

    return selected


def build_context(selected_notes):
    context_parts = []

    for index, note in enumerate(selected_notes, start=1):
        context_parts.append(
            f"""
[Wiki Note {index}]
Title: {note["title"]}
File: {note["file_name"]}
Content Type: {note["content_type"]}
Source URL: {note["source_url"]}

{note["body"]}
"""
        )

    return "\n\n".join(context_parts)


def ask_ollama(prompt):
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    response.raise_for_status()

    data = response.json()
    return data.get("response", "")


def answer_question(question):
    taxonomy = load_json(TAXONOMY_FILE)
    vault_path = taxonomy.get("vault_path")

    if not vault_path:
        raise ValueError("taxonomy.json me vault_path missing hai.")

    notes = load_wiki_notes(vault_path)
    selected_notes = retrieve_notes(question, notes, top_k=3)
    context = build_context(selected_notes)

    prompt = f"""
You are an LLM Wiki assistant for OHSERS Retirement notes.

Use ONLY the wiki context provided below.
Do not use outside knowledge.
If the answer is not present in the context, say:
"I do not have enough information in the current Retirement Wiki."

Answer clearly and simply.

Question:
{question}

Wiki Context:
{context}

Final Answer:
"""

    answer = ask_ollama(prompt)

    print("\nANSWER:\n")
    print(answer.strip())

    print("\nNOTES USED:\n")
    for note in selected_notes:
        print(f"- {note['file_name']} | {note['title']}")


def main():
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        question = input("Ask from Retirement LLM Wiki: ")

    answer_question(question)


if __name__ == "__main__":
    main()