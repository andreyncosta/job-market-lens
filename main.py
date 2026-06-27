"""
job-market-lens — CLI entrypoint.

Usage:
    python main.py collect          # collect from all sources and store
    python main.py stats            # print summary stats from stored data
    python main.py skills           # print top skills from stored data
"""

import argparse
import logging
import os
import sys

from collector import collect_all
from processor import extract_skills, extract_remote_signal
from storage import JobStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def cmd_collect(args):
    logger.info("Starting collection run...")

    jobs = collect_all(
        adzuna_app_id=os.getenv("ADZUNA_APP_ID"),
        adzuna_app_key=os.getenv("ADZUNA_APP_KEY"),
        adzuna_max=args.max,
    )
    logger.info(f"Collected {len(jobs)} raw jobs across all sources")

    with JobStore(args.db) as store:
        store.insert_many(jobs)
        logger.info(f"Total jobs in store: {store.count()}")

        # Skill extraction pass
        df = store.query_df("SELECT id, title, description FROM jobs")
        logger.info(f"Extracting skills from {len(df)} job descriptions...")

        for _, row in df.iterrows():
            skills = extract_skills(row["description"] or "")
            if skills:
                for skill in skills:
                    try:
                        store._con.execute(
                            "INSERT INTO skills (job_id, skill) VALUES (?, ?) ON CONFLICT DO NOTHING",
                            [row["id"], skill],
                        )
                    except Exception as exc:
                        logger.debug(
                            "[skills] Skipped skill %r for job %s: %s",
                            skill,
                            row["id"],
                            exc,
                        )

        logger.info("Skill extraction complete.")


def cmd_stats(args):
    with JobStore(args.db) as store:
        total = store.count()
        print(f"\n{'='*40}")
        print(f"  Total jobs stored : {total}")

        df = store.query_df("""
            SELECT source, COUNT(*) as n, 
                   ROUND(AVG(salary_min),0) as avg_salary_min,
                   SUM(CASE WHEN remote_flag THEN 1 ELSE 0 END) as remote_count
            FROM jobs 
            GROUP BY source
        """)
        print("\nBy source:")
        print(df.to_string(index=False))
        print(f"{'='*40}\n")


def cmd_skills(args):
    top = int(args.top)  # argparse already enforces int; explicit cast guards future refactors
    with JobStore(args.db) as store:
        df = store.query_df(f"""
            SELECT skill, COUNT(*) as frequency,
                   ROUND(100.0 * COUNT(*) / (SELECT COUNT(DISTINCT job_id) FROM skills), 1) as pct_jobs
            FROM skills
            GROUP BY skill
            ORDER BY frequency DESC
            LIMIT {top}
        """)
        print(f"\nTop {top} skills across all collected jobs:\n")
        print(df.to_string(index=False))
        print()


def main():
    parser = argparse.ArgumentParser(prog="job-market-lens")
    parser.add_argument("--db", default="data/jobs.duckdb", help="DuckDB database path")

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_collect = sub.add_parser("collect", help="Run collection from all sources")
    p_collect.add_argument("--max", type=int, default=200, help="Max results per Adzuna query")
    p_collect.set_defaults(func=cmd_collect)

    p_stats = sub.add_parser("stats", help="Print summary statistics")
    p_stats.set_defaults(func=cmd_stats)

    p_skills = sub.add_parser("skills", help="Print top skills")
    p_skills.add_argument("--top", type=int, default=30, help="Number of top skills to show")
    p_skills.set_defaults(func=cmd_skills)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
