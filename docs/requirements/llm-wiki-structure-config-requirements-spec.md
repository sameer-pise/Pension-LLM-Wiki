
# LLM Wiki Structure Config Requirements Specification

## Related Documents
- [LLM Wiki Crawler Requirements](llm-wiki-crawler-requirements-spec.md)
- [LLM Wiki Raw-to-Wiki Structuring Requirements](llm-wiki-raw-to-wiki-structuring-requirements-spec.md)
- [LLM Wiki Structure Config Design](../design/llm-wiki-structure-config-design.md)
- [Wiki LLM Acceptance Criteria](../design/wiki-llm-acceptance-criteria.md)

## 1. Document Control
- Document title: LLM Wiki Structure Config Requirements Specification
- Version: 1.0
- Date: 2026-05-27
- Status: Approved for implementation
- Related design documents:
  - ../design/llm-wiki-crawler-design.md
  - ../design/llm-wiki-markdown-storage-design.md
  - ../design/wiki-llm-implementation-spec.md

## 2. Purpose
Define requirements for a single JSON configuration file (recommended name: wiki-structure-config.json) that drives all pipeline structuring, chunking, and category mapping for the LLM Wiki solution.

## 3. Scope
In scope:
- Category, sub-category, and topic mapping
- Folder and slug pattern control
- Chunking and cleaning rules
- Status and backup policy
- Per-item keyword and processing hints
- Backward compatibility for crawler and raw-to-wiki stages

Out of scope:
- UI configuration
- Embedding/vector index config

## 4. Naming and Location
- File name: wiki-structure-config.json (preferred for clarity)
- Location: pipeline root or config folder
- All pipeline stages must accept the config file path as a parameter

## 5. Functional Requirements
| ID | Requirement Statement | Acceptance Criteria | Related Spec |
|---|---|---|---|
| SC-001 | The config file shall define all main categories, sub-categories, and topics with deterministic slugs. | SCA-001 | [Design Spec](../design/llm-wiki-structure-config-design.md) |
| SC-002 | The config file shall specify raw and wiki root paths. | SCA-002 | [Design Spec](../design/llm-wiki-structure-config-design.md) |
| SC-003 | The config file shall define folder and file naming patterns for all output layers. | SCA-003 | [Raw-to-Wiki Structuring](llm-wiki-raw-to-wiki-structuring-requirements-spec.md) |
| SC-004 | The config file shall include chunking and cleaning rules (min/max words, strategy, merge, etc). | SCA-004 | [Raw-to-Wiki Structuring](llm-wiki-raw-to-wiki-structuring-requirements-spec.md) |
| SC-005 | The config file shall list all allowed status values and backup/skip policies. | SCA-005 | [Design Spec](../design/llm-wiki-structure-config-design.md) |
| SC-006 | Each item shall include per-topic keywords for content selection and chunking. | SCA-006 | [Raw-to-Wiki Structuring](llm-wiki-raw-to-wiki-structuring-requirements-spec.md) |
| SC-007 | The config file shall be versioned with a schema_version field. | SCA-007 | [Design Spec](../design/llm-wiki-structure-config-design.md) |
| SC-008 | All pipeline stages shall load and use the config for structuring, chunking, and output path generation. | SCA-008 | [Design Spec](../design/llm-wiki-structure-config-design.md) |
| SC-009 | The config file shall be validated for schema and required fields at pipeline startup. | SCA-009 | [Acceptance Criteria](../design/wiki-llm-acceptance-criteria.md) |
| SC-010 | The config file shall be backward compatible with existing crawler and raw-to-wiki fields. | SCA-010 | [Crawler Requirements](llm-wiki-crawler-requirements-spec.md) |

## 6. Non-Functional Requirements
| ID | Requirement Statement | Acceptance Criteria |
|---|---|
| SNC-001 | Config changes shall not require code changes for new categories or topics. | SCA-011 |
| SNC-002 | Config file must be valid JSON and parseable by Python and JS. | SCA-012 |
| SNC-003 | Config file must be human-editable and documented. | SCA-013 |

## 7. Acceptance Criteria
| AC ID | Requirement(s) | Acceptance Criteria |
|---|---|---|
| SCA-001 | SC-001 | All categories, sub-categories, and topics are present with unique slugs. |
| SCA-002 | SC-002 | Raw and wiki root paths are used for all file operations. |
| SCA-003 | SC-003 | Output files are written to paths matching the config pattern. |
| SCA-004 | SC-004 | Chunking and cleaning rules are respected in all processed notes. |
| SCA-005 | SC-005 | Only allowed status values are used in output notes. |
| SCA-006 | SC-006 | Per-topic keywords are used for content selection/chunking. |
| SCA-007 | SC-007 | schema_version is present and checked at startup. |
| SCA-008 | SC-008 | All structuring and chunking logic is config-driven, not hardcoded. |
| SCA-009 | SC-009 | Invalid or missing config fields cause pipeline startup failure with clear error. |
| SCA-010 | SC-010 | Existing pipeline features continue to work with new config. |
| SCA-011 | SNC-001 | Adding a new topic or category in config results in new output without code change. |
| SCA-012 | SNC-002 | Config file parses cleanly in Python and JS test harnesses. |
| SCA-013 | SNC-003 | Config file is documented with field descriptions. |

## 8. Definition of Done
- All SC-001 to SC-010 and SNC-001 to SNC-003 requirements are implemented.
- All SCA-001 to SCA-013 acceptance criteria pass.
- No open High severity defects.
- Config file is documented and versioned.
