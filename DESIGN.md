# SuperApp Production Design

## Architecture

FastAPI owns HTTP and dashboard delivery. The orchestrator coordinates ingestion, schema induction, coverage analysis, claim extraction, contradiction classification, graph construction, and scoring. Pydantic models are the domain contract; SQLAlchemy repositories persist replayable analysis documents, stage outputs, findings, and review status.

## Schema induction and vertical priors

Schema induction remains corpus-aware so new topics can be discovered, but curated vertical seed schemas provide stable minimum coverage for legal contracts and company policies. Seed items are loaded from `superapp/schema_library/` and merged with model output by topic.

## Retrieval and graph reasoning

Vector similarity prunes candidate claim pairs before classification. With an average candidate count of $k$, contradiction checks reduce from $\mathcal{O}(n^2)$ to $\mathcal{O}(n \cdot k)$. The resulting typed claim graph preserves source IDs, relation confidence, and reasoning traces for reviewer inspection.

## Cascade and cost control

Every stage resolves a configured fast, mid, or top model through `Settings.get_model_for_stage`. LLM work is bounded with an `asyncio.Semaphore`; independent chunks and pairs run through `asyncio.gather`. `BillingTracker` records prompt/completion estimates and rejects jobs over token or cost budgets. Results expose normalized usage and cost metadata.

## Storage evolution

SQLite is the zero-configuration development backend. The same SQLAlchemy models support PostgreSQL through `DATABASE_URL`; Alembic owns future schema evolution. JSON stage snapshots make completed analyses reproducible while normalized findings and claim relations support filtering and review workflows.

## Security and tenancy

API-key authentication is enabled by setting `AUTH_PROVIDER=api_key` and `API_KEY`. Development mode intentionally uses a deterministic default tenant. Production requests can supply organization, workspace, and project headers, while role dependencies gate analysis and review operations.