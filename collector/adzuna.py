"""
Adzuna collector — fetches Data Scientist job listings from the Adzuna API.
Docs: https://developer.adzuna.com/
"""

import os
import time
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterator

import httpx

logger = logging.getLogger(__name__)

ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs"
DEFAULT_QUERIES = ["data scientist", "data engineer", "machine learning engineer"]
DEFAULT_COUNTRY = "us"
PAGE_SIZE = 50  # Adzuna max per page


@dataclass
class RawJob:
    source: str
    external_id: str
    title: str
    company: str
    location: str
    description: str
    url: str
    salary_min: float | None
    salary_max: float | None
    remote_flag: bool
    collected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    raw: dict = field(default_factory=dict)


class AdzunaCollector:
    """
    Paginated collector for Adzuna job listings.

    Usage:
        collector = AdzunaCollector(app_id="...", app_key="...")
        for job in collector.collect(queries=["data scientist"], max_results=500):
            print(job.title, job.company)
    """

    def __init__(
        self,
        app_id: str | None = None,
        app_key: str | None = None,
        country: str = DEFAULT_COUNTRY,
        rate_limit_delay: float = 0.5,
    ):
        self.app_id = app_id or os.environ["ADZUNA_APP_ID"]
        self.app_key = app_key or os.environ["ADZUNA_APP_KEY"]
        self.country = country
        self.rate_limit_delay = rate_limit_delay
        self._client = httpx.Client(timeout=15.0)

    def _fetch_page(self, query: str, page: int) -> dict:
        url = f"{ADZUNA_BASE}/{self.country}/search/{page}"
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "results_per_page": PAGE_SIZE,
            "what": query,
            "content-type": "application/json",
        }
        resp = self._client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _parse(raw: dict) -> RawJob:
        loc = raw.get("location", {})
        location_str = ", ".join(loc.get("display_name", "").split(",")[:2])

        title = raw.get("title", "")
        desc = raw.get("description", "")
        remote_flag = any(
            kw in (title + desc).lower()
            for kw in ("remote", "work from home", "wfh", "fully remote")
        )

        return RawJob(
            source="adzuna",
            external_id=str(raw.get("id", "")),
            title=title,
            company=raw.get("company", {}).get("display_name", ""),
            location=location_str,
            description=desc,
            url=raw.get("redirect_url", ""),
            salary_min=raw.get("salary_min"),
            salary_max=raw.get("salary_max"),
            remote_flag=remote_flag,
            raw=raw,
        )

    def collect(
        self,
        queries: list[str] = DEFAULT_QUERIES,
        max_results: int = 500,
    ) -> Iterator[RawJob]:
        """Yield RawJob objects across all queries, paginating until max_results."""
        seen_ids: set[str] = set()

        for query in queries:
            collected = 0
            page = 1

            logger.info(f"[adzuna] Starting query='{query}'")

            while collected < max_results:
                try:
                    data = self._fetch_page(query, page)
                except httpx.HTTPStatusError as e:
                    logger.error(f"[adzuna] HTTP {e.response.status_code} on page {page}: {e}")
                    break

                results = data.get("results", [])
                if not results:
                    logger.info(f"[adzuna] No more results for '{query}' at page {page}")
                    break

                for raw in results:
                    job = self._parse(raw)
                    if job.external_id in seen_ids:
                        continue
                    seen_ids.add(job.external_id)
                    yield job
                    collected += 1
                    if collected >= max_results:
                        break

                logger.info(f"[adzuna] query='{query}' page={page} collected={collected}")
                page += 1
                time.sleep(self.rate_limit_delay)

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
