
# LLM Wiki Structure Config Design Specification

## Related Documents
- [LLM Wiki Structure Config Requirements](../requirements/llm-wiki-structure-config-requirements-spec.md)
- [LLM Wiki Raw-to-Wiki Structuring Requirements](../requirements/llm-wiki-raw-to-wiki-structuring-requirements-spec.md)
- [LLM Wiki Crawler Requirements](../requirements/llm-wiki-crawler-requirements-spec.md)
- [Wiki LLM Acceptance Criteria](wiki-llm-acceptance-criteria.md)

## 1. Overview
This document describes the design for a unified configuration file (wiki-structure-config.json) that drives all structuring, chunking, and output mapping for the LLM Wiki pipeline. The config enables deterministic, auditable, and maintainable processing from raw input to final wiki output.

## 2. Design Goals
- All pipeline structuring and chunking logic is config-driven
- No hardcoded category, folder, or chunking rules in code
- Easy to add new categories/topics by editing config only
- Deterministic output paths and folder structure
- Human-editable, versioned, and documented config

## 3. Config File Schema (JSON)
```json
{
  "schema_version": "1.0",
  "raw_root": "Obsidian/Vault/raw/",
  "wiki_root": "Obsidian/Vault/wiki/",
  "categories": [
    {
      "slug": "member-benefits",
      "title": "Member Benefits",
      "subcategories": [
        {
          "slug": "retirement",
          "title": "Retirement",
          "topics": [
            {
              "slug": "benefit-calculation",
              "title": "Benefit Calculation",
              "keywords": ["calculation", "formula", "estimate"],
              "wiki_output_path": "member-benefits/retirement/benefit-calculation.md",
              "chunking": {
                "min_words": 100,
                "max_words": 400,
                "strategy": "semantic",
                "merge_short": true
              },
              "status": "active"
            }
            // ... more topics ...
          ]
        }
        // ... more subcategories ...
      ]
    }
    // ... more categories ...
  ],
  "status_values": ["active", "draft", "archived"],
  "backup_policy": {
    "enabled": true,
    "retention_days": 30
  }
}
```

## 4. Field Descriptions
- `schema_version`: Version of the config schema
- `raw_root`, `wiki_root`: Root folders for input and output
- `categories`: List of main categories
  - `slug`: Deterministic folder name
  - `title`: Human-readable name
  - `subcategories`: List of subcategories
    - `slug`, `title`: As above
    - `topics`: List of topics
      - `slug`, `title`: As above
      - `keywords`: For content selection/chunking
      - `wiki_output_path`: Deterministic output path
      - `chunking`: Rules for splitting content
      - `status`: One of `status_values`
- `status_values`: Allowed status values
- `backup_policy`: Backup/retention settings

## 5. Usage Patterns
- All pipeline scripts accept the config file path as a parameter
- At startup, pipeline validates config schema and required fields
- All structuring, chunking, and output path logic is driven by config
- Adding a new topic/category only requires editing the config
- Config is documented and versioned

## 6. Example Usage in Pipeline
```python
# Load config
with open('wiki-structure-config.json') as f:
    config = json.load(f)

# Use config for output path
def get_output_path(category_slug, subcat_slug, topic_slug):
    for cat in config['categories']:
        if cat['slug'] == category_slug:
            for sub in cat['subcategories']:
                if sub['slug'] == subcat_slug:
                    for topic in sub['topics']:
                        if topic['slug'] == topic_slug:
                            return topic['wiki_output_path']
    raise ValueError('Not found')
```

## 7. Validation and Error Handling
- On pipeline startup, validate:
  - JSON syntax
  - Required fields present
  - All slugs unique at each level
  - All output paths unique
  - All status values valid
- Fail fast with clear error if validation fails

## 8. Extensibility
- To add a new topic, add to config and re-run pipeline
- To change chunking, edit topic's chunking field
- To add new status, update status_values

## 9. Versioning and Documentation
- schema_version must be incremented for breaking changes
- All fields documented in this design
- Example config provided in repo

## 10. Security and Audit
- Config changes are tracked in version control
- All pipeline runs log the config version used

---
End of design document.
