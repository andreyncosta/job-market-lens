"""
processor.skills — extracts technical skills from job descriptions.

Uses a curated taxonomy of DS/ML/DE skills matched via regex.
Designed to be the first layer before any LLM enrichment.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Skill taxonomy
# Each entry: (canonical_name, [regex_patterns])
# Patterns are matched case-insensitively against the full job description.
# ---------------------------------------------------------------------------
SKILL_TAXONOMY: list[tuple[str, list[str]]] = [
    # Languages
    ("python", [r"\bpython\b"]),
    # NOTE: "\br\b" with IGNORECASE is intentionally omitted — it matches any
    # standalone letter "r" in text (e.g. in abbreviations, bullet points, etc.)
    # producing high false-positive rates. "R programming" and "R language" are
    # sufficient to capture genuine R skill mentions.
    ("r", [r"\bR programming\b", r"\bR language\b", r"\bin R\b"]),
    ("sql", [r"\bsql\b"]),
    ("scala", [r"\bscala\b"]),
    ("java", [r"\bjava\b"]),
    ("julia", [r"\bjulia\b"]),

    # Big Data
    ("spark", [r"\bspark\b", r"\bpyspark\b", r"\bapache spark\b"]),
    ("hive", [r"\bhive\b", r"\bhiveql\b"]),
    ("hadoop", [r"\bhadoop\b"]),
    ("kafka", [r"\bkafka\b"]),
    ("airflow", [r"\bairflow\b"]),
    ("dbt", [r"\bdbt\b"]),
    ("flink", [r"\bflink\b"]),
    ("impala", [r"\bimpala\b"]),

    # ML / DL Frameworks
    ("scikit-learn", [r"\bscikit[\-\s]?learn\b", r"\bsklearn\b"]),
    ("pytorch", [r"\bpytorch\b", r"\btorch\b"]),
    ("tensorflow", [r"\btensorflow\b", r"\btf\b"]),
    ("keras", [r"\bkeras\b"]),
    ("xgboost", [r"\bxgboost\b"]),
    ("lightgbm", [r"\blightgbm\b"]),
    ("catboost", [r"\bcatboost\b"]),

    # LLMs / GenAI
    ("llm", [r"\bllm\b", r"\blarge language model\b"]),
    ("rag", [r"\brag\b", r"\bretrieval[\-\s]augmented\b"]),
    ("langchain", [r"\blangchain\b"]),
    ("openai", [r"\bopenai\b", r"\bgpt[\-\s]?[34]\b", r"\bchatgpt\b"]),
    ("huggingface", [r"\bhugging\s?face\b", r"\btransformers\b"]),
    ("prompt-engineering", [r"\bprompt\s?engineer\b"]),
    ("agents", [r"\bagent[\-\s]?based\b", r"\bagentic\b", r"\bai agent\b"]),

    # MLOps
    ("mlflow", [r"\bmlflow\b"]),
    ("kubeflow", [r"\bkubeflow\b"]),
    ("docker", [r"\bdocker\b"]),
    ("kubernetes", [r"\bkubernetes\b", r"\bk8s\b"]),
    ("fastapi", [r"\bfastapi\b"]),

    # Cloud
    ("aws", [r"\baws\b", r"\bamazon web services\b"]),
    ("gcp", [r"\bgcp\b", r"\bgoogle cloud\b"]),
    ("azure", [r"\bazure\b"]),
    ("databricks", [r"\bdatabricks\b"]),
    ("snowflake", [r"\bsnowflake\b"]),

    # Stats / Math
    ("statistics", [r"\bstatistic\b", r"\bstatistical\b"]),
    ("econometrics", [r"\beconometr\b"]),
    ("bayesian", [r"\bbayesian\b"]),
    ("causal-inference", [r"\bcausal\s?inference\b", r"\bdid\b", r"\biv estimation\b", r"\binstrumental variable\b"]),
    ("time-series", [r"\btime[\-\s]?series\b", r"\barima\b", r"\bprophet\b"]),
    ("ab-testing", [r"\ba/b test\b", r"\bexperimentation\b"]),

    # Visualization
    ("power-bi", [r"\bpower\s?bi\b"]),
    ("tableau", [r"\btableau\b"]),
    ("matplotlib", [r"\bmatplotlib\b"]),
    ("plotly", [r"\bplotly\b"]),

    # Databases
    ("postgresql", [r"\bpostgres\b", r"\bpostgresql\b"]),
    ("mongodb", [r"\bmongodb\b"]),
    ("elasticsearch", [r"\belasticsearch\b"]),
    ("redis", [r"\bredis\b"]),

    # Domain
    ("fintech", [r"\bfintech\b"]),
    ("nlp", [r"\bnlp\b", r"\bnatural language processing\b"]),
    ("computer-vision", [r"\bcomputer\s?vision\b", r"\bcv\b"]),
    ("anomaly-detection", [r"\banomaly\s?detection\b"]),
    ("recommendation-systems", [r"\brecommend(ation)?\s?system\b"]),
    ("entity-resolution", [r"\bentity\s?resolution\b"]),
]

# Pre-compile all patterns
_COMPILED: list[tuple[str, list[re.Pattern]]] = [
    (name, [re.compile(p, re.IGNORECASE) for p in patterns])
    for name, patterns in SKILL_TAXONOMY
]


@dataclass
class SkillExtractionResult:
    job_id: str
    skills: list[str]


def extract_skills(text: str) -> list[str]:
    """
    Extract canonical skill names from a job description string.
    Returns a sorted, deduplicated list.
    """
    found: set[str] = set()
    for name, patterns in _COMPILED:
        if any(p.search(text) for p in patterns):
            found.add(name)
    return sorted(found)


def extract_remote_signal(text: str) -> bool:
    """Check whether a job description contains strong remote-work signals.

    Returns True if the text contains phrases that explicitly indicate a
    fully-remote position (e.g. "fully remote", "100% remote", "work from
    anywhere").  This is a *stricter* signal than the collector-level
    ``remote_flag``, which also triggers on the broader word "remote".

    .. note::
        This function is not currently called anywhere in the pipeline.
        It is intended to be used as a post-collection enrichment step —
        for example, to add a ``strong_remote`` column in ``JobStore`` or
        to re-score listings whose ``remote_flag`` was set only because the
        word "remote" appeared incidentally.  Wire it in via
        ``collect_all`` or as a separate ``cmd_enrich`` CLI command.
    """
    patterns = [
        r"\bfully remote\b",
        r"\b100%\s?remote\b",
        r"\bwork from anywhere\b",
        r"\bremote[\-\s]first\b",
        r"\bglobal remote\b",
        r"\bremote worldwide\b",
    ]
    combined = "|".join(patterns)
    return bool(re.search(combined, text, re.IGNORECASE))
