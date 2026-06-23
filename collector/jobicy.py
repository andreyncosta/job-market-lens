"""
Jobicy collector — fetches remote-only job listings from Jobicy's public JSON feed.
Docs: https://jobicy.com/jobs-rss-feed
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterator

import httpx

from collector.adzuna import RawJob

logger = logging.getLogger(__name__)

JOBICY_FEED = "https://jobicy.com/api/v2/remote-jobs"
DEFAULT_TAGS = ["data-scientist", "machine-learning", "data-engineer"]


class JobicyCollector:
    """
    Collector for Jobicy remote job listings (no API key required).

    Usage:
        collector = JobicyCollector()
        for job in collector.collect(tags=["data-scientist"]):
            print(job.title, job.company)
    """

    def __init__(self, count: int = 50):
        self.count = min(count, 50)  # Jobicy max = 50
        self._client = httpx.Client(timeout=15.0)

    def _fetch(self, tag: str) -> list[dict]:
        params = {"count": self.count, "tag": tag}
        resp = self._client.get(JOBICY_FEED, params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("jobs", [])

    @staticmethod
    def _parse(raw: dict) -> RawJob:
        title = raw.get("jobTitle", "")
        desc = raw.get("jobDescription", "")
        location = raw.get("jobGeo", "Worldwide")

        return RawJob(
            source="jobicy",
            external_id=str(raw.get("id", "")),
            title=title,
            company=raw.get("companyName", ""),
            location=location,
            description=desc,
            url=raw.get("url", ""),
            salary_min=None,
            salary_max=None,
            remote_flag=True,  # Jobicy is remote-only by design
            raw=raw,
        )

    def collect(self, tags: list[str] = DEFAULT_TAGS) -> Iterator[RawJob]:
        """Yield RawJob objects for each tag."""
        seen_ids: set[str] = set()

        for tag in tags:
            logger.info(f"[jobicy] Fetching tag='{tag}'")
            try:
                results = self._fetch(tag)
            except httpx.HTTPStatusError as e:
                logger.error(f"[jobicy] HTTP {e.response.status_code} for tag '{tag}': {e}")
                continue

            for raw in results:
                job = self._parse(raw)
                if job.external_id in seen_ids:
                    continue
                seen_ids.add(job.external_id)
                yield job

            logger.info(f"[jobicy] tag='{tag}' → {len(results)} jobs")

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
