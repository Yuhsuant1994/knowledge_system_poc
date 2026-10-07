# Knowledge System

A single `/chat` fastapi endpoint orchestrating 3 agents:

1. HR handbook RAG (pgvector)
2. Sales text2SQL (Postgres)
3. Github agent (github MCP)

Along with streamlit UI for demo purpose. Everything runs on open models via Ollama, git credential is a temp key with readonly access for demo purpose.

## Data sources

| Domain | Source | Notes |
|---|---|---|
| Sales | [drizzle-team/drizzle-northwind-benchmarks-pg](https://github.com/drizzle-team/drizzle-northwind-benchmarks-pg) (`data/init-db.sql`) | real classic Northwind dataset; downloaded fresh by `ingestion/sales_fetch.py` at setup time, order dates rescaled into 2026 so it reads as recent. Nothing committed to git. |
| HR handbook | [PostHog/posthog.com](https://github.com/PostHog/posthog.com), `contents/handbook/company/**` | PostHog's real public handbook. Crawled live by `ingestion/hr/`, nothing committed to git. |
| Dev / GitHub | [coroot/coroot](https://github.com/coroot/coroot) | real open-source observability tool, accessed read-only via MCP server. |

## Permission control

To demostrate the availablity for access control, I've setup role mechanism, it comes from the `users` table (created from`postgres/init/init.sql`), looked up
via `GET /access?username=...` and enforced server-side in every `/chat` call.

| Role | Login | hr_rag | sales_sql | github |
|---|---|---|---|---|
| admin | Hsuan AD | ✅ | ✅ | ✅ |
| user | Hsuan US | ✅ | ❌ | ❌ |
| dev | Hsuan DE | ✅ | ✅ | ✅ |
| sales | Hsuan SA | ✅ | ✅ | ❌ |



## Local Setup

```bash
make up            # docker compose up for all the resources
make pull-model    # pulls OLLAMA_MODEL + EMBEDDING_MODEL in ollama
make fetch-sales   # downloads + loads real Northwind data
make hr-init       # crawls PostHog handbook/company, process data to vector store
```

after it's done we can see http://localhost:8501 for streamlit app, and http://localhost:8000/docs for api swagger


## Testing Locally

to run the test locally we can do below command however it would be implement in CICD

```bash
poetry install
make test
```

## Architecture

{image placeholder}

### Design decisions:

1. Why pgvector? easier with Postgres db (already in the system for sales data), and the complexity of the project doesn't need to use other dedicated services like Elasticsearch.
2. Why llama3.2:1b: due to the resouce limitation and limited to opensource. Want to get a trade off between speed.
3. why chunk 1024? it's a common default RAG chunking, and `lama3.2:1b` perform more stable within 4000-5000 token, retrieving `top_k=3` adding system prompt this fit well with the context.
4. overlap 200 token: generally speaking a paragrah is around 150-200 token, by doing so we are less likely to loss information
5. Why langgraph over A2A:
  * this usecase is more routing than needed agent to co-work with agent.
  * langraph routing is deterministic code, so we can have better control for the permission.


### Design trade-offs:

1. Smaller-model -> open source and local laptop resource limitation.
2. Github MCP hardcode limit -> limit the max_comment and timeout second, all these approach is for demo purpose to reduce context length.
3. Adding keyword detection to skip routing classifier part -> it is dangerous approach, but it's to speed up some process, future better have a intent table to support this steps.
4. Hardcode sales schema for text2sql-> work fine with small dataset, but need a more sophisticate design for this part.
5. Not implemented follow up question-> due to the time for implementation, it can be future options, which need to align the cache logic with business concept.
