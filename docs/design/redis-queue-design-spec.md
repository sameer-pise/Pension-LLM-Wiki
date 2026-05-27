# Recommended Task Queue Libraries

For managing distributed and background task queues in the LLM Wiki pipeline, the following Python libraries are recommended:

- **Celery** ([celeryproject.org](https://docs.celeryq.dev/)): The most widely used asynchronous task queue/job queue based on distributed message passing. Supports multiple brokers (including Redis), robust scheduling, retries, and monitoring. Best for large-scale, production workloads.
- **Dramatiq** ([dramatiq.io](https://dramatiq.io/)): Fast and reliable background task processing library for Python 3. Simple API, supports Redis and RabbitMQ, and is easy to integrate.
- **RQ (Redis Queue)** ([python-rq.org](https://python-rq.org/)): Simple job queues for Python using Redis. Lightweight and easy to set up for smaller projects or prototyping.
- **Huey** ([huey.readthedocs.io](https://huey.readthedocs.io/)): Small multi-threaded task queue with Redis support. Good for lightweight or embedded use cases.
- **Taskiq** ([taskiq-python.github.io](https://taskiq-python.github.io/)): Distributed task queue with native asyncio support and pluggable brokers. Modern and async-native.

**Recommendation:**
- Use **Celery** for robust, production-grade distributed task management.
- Use **Dramatiq** or **Taskiq** for modern, async-native Python projects.
- Use **RQ** or **Huey** for simple, lightweight, or prototyping needs.

All of these libraries support Redis as a broker and can be integrated with the queue separation model described above.

# Redis Queue Design Spec

## Related Documents
- [LLM Wiki Crawler Design](llm-wiki-crawler-design.md)
- [LLM Wiki Crawler Requirements](../requirements/llm-wiki-crawler-requirements-spec.md)
- [Wiki LLM Implementation Spec](wiki-llm-implementation-spec.md)

## Purpose
Use Redis-backed queues to separate crawler work from heavy processing tasks.

The crawler must stay fast.
Workers handle slow jobs.

---

## Architecture

```text
Crawler
  ↓
URL Classifier
  ↓
Redis Queues
  ↓
Specialized Workers
  ↓
Storage
```

## Goals
- Decouple discovery from processing.
- Keep crawl latency low and predictable.
- Isolate failures by job type.
- Enable horizontal worker scaling.
- Preserve deterministic processing and traceability.

## Non-Goals
- Real-time streaming guarantees.
- Exactly-once delivery semantics from Redis itself.

## Queue Separation Model
Use dedicated queues per job type:

1. crawl.url_discovery
- Producer: crawler URL classifier.
- Consumer: crawl worker.
- Job: crawl internal HTML URL and emit discovered links.

2. doc.pdf_download_convert
- Producer: URL classifier.
- Consumer: document worker.
- Job: download PDF and convert to markdown.

3. media.youtube_transcript
- Producer: URL classifier.
- Consumer: YouTube worker.
- Job: metadata + captions extraction; Whisper fallback only.

4. system.retry
- Producer: all workers.
- Consumer: retry worker.
- Job: delayed retry for transient failures.

5. system.dead_letter
- Producer: all workers after retry exhaustion.
- Consumer: ops/manual replay tools.
- Job: terminal failed jobs for audit and replay.

## Redis Data Structures
Recommended default:
- Redis Streams for durability and consumer groups.

Stream keys:
- queue:crawl:url_discovery
- queue:doc:pdf_download_convert
- queue:media:youtube_transcript
- queue:system:retry
- queue:system:dead_letter

Consumer groups:
- cg:crawl
- cg:doc
- cg:media
- cg:retry

Alternative (simpler) option:
- Redis Lists with BRPOP/LPUSH, if Streams are not required.

## Message Contract
Every queue message must include:
- job_id: stable unique id (uuid or deterministic hash)
- job_type: crawl_url | pdf_convert | youtube_transcript
- source_url: canonical URL
- parent_url: optional parent URL
- discovered_at_utc: ISO-8601
- crawl_id: run identifier
- depth: integer
- attempt: integer starting at 1
- max_attempts: integer
- priority: low | normal | high
- idempotency_key: deterministic key for dedupe
- payload: object with job-specific fields

Job-specific payload examples:

crawl_url payload:
- allowed_domain
- allowed_paths
- timeout_seconds

pdf_convert payload:
- target_storage_path
- filename_hint

youtube_transcript payload:
- video_id
- whisper_enabled

## Producer Rules
- Crawler must only classify and enqueue; avoid heavy processing in crawler process.
- Canonicalize URL before enqueue.
- Set idempotency_key as hash(job_type + canonical_url).
- Do not enqueue external links.
- Non-PDF documents are not enqueued to pdf queue; log and skip.

## Worker Rules
- Workers process only their queue type.
- Workers must be idempotent:
  - check if artifact already exists and is valid before processing.
- On success:
  - write output atomically,
  - emit success log,
  - acknowledge queue message.
- On transient error:
  - enqueue to retry queue with backoff schedule and incremented attempt.
- On terminal error:
  - push to dead letter queue with full error context.

## Retry and Backoff Policy
- Default max_attempts: 3
- Backoff: exponential with jitter
- Example delays: 30s, 120s, 300s
- Retry eligibility:
  - network timeout
  - rate limit
  - temporary service unavailable
- Non-retryable errors:
  - unsupported file type
  - invalid URL format
  - permanent 404 after verification

## Dead Letter Policy
DLQ record must include:
- original message
- failed_at_utc
- worker_name
- error_type
- error_message
- stack_trace (if available)
- last_attempt

Replay rules:
- replay tool may requeue DLQ item after operator approval.
- replay must create new job_id and preserve original_job_id reference.

## Ordering and Throughput
- No global ordering guarantee required.
- Per-URL ordering is best-effort.
- Scale by increasing worker replicas per queue.
- Set max in-flight per worker to control memory and external API load.

## Idempotency and Deduplication
- Use idempotency_key at enqueue time to avoid duplicate jobs.
- Use storage existence + checksum validation at worker time.
- Keep processed key in Redis with TTL for short-term dedupe.

Suggested Redis key:
- dedupe:{idempotency_key} -> processed marker, TTL 7 days

## Storage Outputs
crawl.url_discovery output:
- raw markdown files with frontmatter

doc.pdf_download_convert output:
- downloaded PDF (optional retain policy)
- converted markdown file

media.youtube_transcript output:
- storage/youtube/{video_id}/metadata.json
- storage/youtube/{video_id}/raw_segments.jsonl
- storage/youtube/{video_id}/status.json
- storage/youtube/{video_id}/errors.jsonl

## Observability
Log required fields on every queue event:
- timestamp
- level
- event
- queue_name
- job_id
- job_type
- source_url
- attempt
- crawl_id
- status
- details

Required events:
- queue_enqueue
- queue_dequeue
- worker_started
- worker_succeeded
- worker_retry_scheduled
- worker_failed_terminal
- dlq_pushed

Metrics to expose:
- queue depth per queue
- worker throughput per queue
- success/failure/retry counts
- DLQ growth rate
- processing latency p50/p95/p99

## Security and Safety
- Redis authentication required.
- TLS required if Redis is remote.
- Namespaced keys for environment isolation (dev/stage/prod).
- Validate and sanitize URLs before enqueue.

## Configuration
Minimum config keys:
- redis_url
- redis_prefix
- queue_enabled
- worker_concurrency.crawl
- worker_concurrency.doc
- worker_concurrency.media
- retry.max_attempts
- retry.base_delay_seconds
- retry.max_delay_seconds
- dlq.enabled

## Rollout Plan
Phase 1:
- Implement crawl queue + crawl worker.

Phase 2:
- Add PDF queue + document worker.

Phase 3:
- Add YouTube queue + transcript worker.

Phase 4:
- Add retry worker + DLQ + replay tooling + dashboards.

## Acceptance Criteria
- Crawler enqueue path adds no heavy processing and remains responsive.
- Queue-specific workers process only their designated job types.
- Retry and DLQ behavior matches policy.
- Duplicate jobs do not create duplicate artifacts.
- Logs and metrics allow root-cause analysis for failures.
