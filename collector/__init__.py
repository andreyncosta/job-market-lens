"""
collector — unified job collection pipeline.

Orchestrates multiple source collectors and deduplicates results by external_id.
"""

from collector.adzuna import AdzunaCollector, RawJob
from collector.jobicy import JobicyCollector

__all__ = ["AdzunaCollector", "JobicyCollector", "RawJob", "collect_all"]


def collect_all(
    adzuna_app_id: str | None = None,
    adzuna_app_key: str | None = None,
    adzuna_queries: list[str] | None = None,
    adzuna_max: int = 500,
    jobicy_tags: list[str] | None = None,
) -> list[RawJob]:
    """
    Run all collectors and return a deduplicated list of RawJob objects.

    Sources:
      - Adzuna (US market, requires free API key)
      - Jobicy (remote-only, no key required)
    """
    jobs: list[RawJob] = []
    seen: set[str] = set()

    def _dedup_add(job: RawJob):
        key = f"{job.source}:{job.external_id}"
        if key not in seen:
            seen.add(key)
            jobs.append(job)

    # Adzuna
    try:
        with AdzunaCollector(app_id=adzuna_app_id, app_key=adzuna_app_key) as az:
            for job in az.collect(
                queries=adzuna_queries or ["data scientist", "machine learning engineer"],
                max_results=adzuna_max,
            ):
                _dedup_add(job)
    except KeyError:
        print("[collect_all] Adzuna credentials not set — skipping.")

    # Jobicy
    with JobicyCollector() as jc:
        for job in jc.collect(tags=jobicy_tags or ["data-scientist", "machine-learning"]):
            _dedup_add(job)

    return jobs
