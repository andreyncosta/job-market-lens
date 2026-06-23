# job-market-lens

> Systematic intelligence on the Data Science job market.

A data collection and analysis pipeline that aggregates job listings from multiple sources, extracts technical skills, and maps the US Data Science hiring landscape — with a focus on remote opportunities.

Built as both a personal job search tool and a portfolio ML project.

---

## What it does

```
collect → store → extract skills → analyze → (upcoming) visualize
```

1. **Collect** — pulls listings from Adzuna (US market aggregator) and Jobicy (remote-only)
2. **Store** — persists raw jobs in a local DuckDB database, deduplicating by source + ID
3. **Extract** — runs a curated regex taxonomy over descriptions to tag 60+ technical skills
4. **Analyze** — CLI commands for skill frequency, salary distributions, remote signal detection

## Stack

| Layer | Technology |
|---|---|
| Collection | Python · httpx · Adzuna API · Jobicy JSON feed |
| Storage | DuckDB (embedded, zero-server) |
| Processing | regex taxonomy · pandas |
| CLI | argparse |
| Upcoming | LLM enrichment · Streamlit dashboard · scikit-learn clustering |

## Quickstart

```bash
git clone https://github.com/andreyncosta/job-market-lens
cd job-market-lens

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Add your Adzuna credentials (free at https://developer.adzuna.com/)
```

### Collect jobs

```bash
python main.py collect --max 300
```

Jobicy requires no credentials. Adzuna requires a free API key.

### Inspect results

```bash
python main.py stats          # summary by source + remote count
python main.py skills --top 40  # top skills by frequency
```

## Project structure

```
job-market-lens/
├── collector/
│   ├── adzuna.py       # Adzuna REST API collector (paginated)
│   ├── jobicy.py       # Jobicy JSON feed collector
│   └── __init__.py     # collect_all() unified pipeline
├── processor/
│   ├── skills.py       # regex-based skill extractor (60+ skills)
│   └── __init__.py
├── storage/
│   ├── store.py        # DuckDB wrapper
│   └── __init__.py
├── data/               # .gitignored — local DuckDB lives here
├── main.py             # CLI entrypoint
├── requirements.txt
└── .env.example
```

## Skill taxonomy

The extractor covers:

- **Languages**: Python, R, SQL, Scala, Java, Julia
- **Big Data**: Spark, Hive, Hadoop, Kafka, Airflow, Impala, dbt
- **ML/DL**: scikit-learn, PyTorch, TensorFlow, XGBoost, LightGBM
- **LLMs/GenAI**: LLM, RAG, LangChain, OpenAI, HuggingFace, agents
- **MLOps**: MLflow, Docker, Kubernetes, FastAPI
- **Cloud**: AWS, GCP, Azure, Databricks, Snowflake
- **Stats**: Bayesian, causal inference, time series, A/B testing, econometrics
- **Viz**: Power BI, Tableau, Plotly

## Roadmap

- [ ] LLM enrichment layer — structured extraction of seniority, visa sponsorship, true remote status
- [ ] Streamlit dashboard — interactive skill frequency charts, salary distributions
- [ ] Clustering — unsupervised grouping of job profiles by skill co-occurrence
- [ ] Profile gap analysis — compare your skillset against market demand distribution
- [ ] Automated daily collection via cron / GitHub Actions

---

**Andrey Costa** · [andreycosta.com](https://andreycosta.com) · Brasília, Brazil
