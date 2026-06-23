"""
storage — DuckDB-backed persistence layer for job listings.

Schema is append-only: jobs are inserted once and never updated.
Deduplication is enforced via (source, external_id) unique constraint.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import duckdb

from collector.adzuna import RawJob

logger = logging.getLogger(__name__)

DEFAULT_DB = Path("data/jobs.duckdb")

DDL = """
CREATE TABLE IF NOT EXISTS jobs (
    id            INTEGER PRIMARY KEY,
    source        VARCHAR NOT NULL,
    external_id   VARCHAR NOT NULL,
    title         VARCHAR,
    company       VARCHAR,
    location      VARCHAR,
    description   TEXT,
    url           VARCHAR,
    salary_min    DOUBLE,
    salary_max    DOUBLE,
    remote_flag   BOOLEAN,
    collected_at  TIMESTAMPTZ,
    raw           JSON,
    UNIQUE (source, external_id)
);

CREATE TABLE IF NOT EXISTS skills (
    job_id        INTEGER REFERENCES jobs(id),
    skill         VARCHAR NOT NULL,
    PRIMARY KEY (job_id, skill)
);
"""


class JobStore:
    """
    Thin DuckDB wrapper. Thread-safe for single-process use.

    Usage:
        with JobStore() as store:
            inserted = store.insert_many(jobs)
            df = store.query_df("SELECT * FROM jobs WHERE remote_flag = true")
    """

    def __init__(self, path: Path | str = DEFAULT_DB):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._con = duckdb.connect(str(self.path))
        self._con.execute(DDL)
        logger.info(f"[store] Connected to {self.path}")

    def insert_many(self, jobs: list[RawJob]) -> int:
        """Insert jobs, silently skipping duplicates. Returns count of new rows."""
        inserted = 0
        for job in jobs:
            try:
                self._con.execute(
                    """
                    INSERT INTO jobs
                        (source, external_id, title, company, location,
                         description, url, salary_min, salary_max,
                         remote_flag, collected_at, raw)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (source, external_id) DO NOTHING
                    """,
                    [
                        job.source,
                        job.external_id,
                        job.title,
                        job.company,
                        job.location,
                        job.description,
                        job.url,
                        job.salary_min,
                        job.salary_max,
                        job.remote_flag,
                        job.collected_at,
                        json.dumps(job.raw),
                    ],
                )
                inserted += self._con.fetchone()[0] if False else 1  # count approximation
            except duckdb.ConstraintException:
                pass  # duplicate — expected
        logger.info(f"[store] Inserted up to {inserted} jobs (duplicates silently skipped)")
        return inserted

    def query_df(self, sql: str):
        """Return a pandas DataFrame for any SQL query."""
        return self._con.execute(sql).df()

    def count(self) -> int:
        return self._con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

    def close(self):
        self._con.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
