# Knowledge System

A single `/chat` fastapi endpoint orchestrating 3 agents:

1. HR handbook RAG (pgvector)
2. Sales text2SQL (Postgres)
3. Github agent (github MCP)

Along with streamlit UI for demo purpose. Everything runs on open models via Ollama; the GitHub agent needs your own read-only token (see Local Setup below).

## Project assumption

In this project I've made some assumption to simulate the enterprise setup.
* Single DB: one Postgres instance
* Local LLM: not using AI gateway, google/openAI api
* HR/Sales/Github domain are separate: no question would be ask for cross agent infomation (which is often not the case in realword).

## Architecture

![Architecture](./architecture.png)

### Component selection reason

1. Why pgvector? easier with Postgres db (already in the system for sales data), and the complexity of the project doesn't need to use other dedicated services like Elasticsearch.
2. Why llama3.2:1b: due to the resouce limitation and limited to opensource. Want to get a trade off between speed.
3. Why FastAPI? need async for the github agent's MCP calls, plus pydantic validation and native support swagger docs.
4. Why langgraph over A2A:
  * this usecase is more routing than needed agent to co-work with agent.
  * langraph routing is deterministic code, so we can have better control for the permission.

## Data connection
| Domain | Source | Connection | Notes |
|---|---|---|---|
| Sales | [drizzle-team/drizzle-northwind-benchmarks-pg](https://github.com/drizzle-team/drizzle-northwind-benchmarks-pg) (`data/init-db.sql`) | Postgres | real classic Northwind dataset; downloaded fresh by `ingestion/sales_fetch.py` at setup time, order dates rescaled into 2026 so it reads as recent. Nothing committed to git. |
| HR handbook | [PostHog/posthog.com](https://github.com/PostHog/posthog.com), `contents/handbook/company/**` | Live GitHub crawl | PostHog's real public handbook. Crawled live by `ingestion/hr/`, nothing committed to git. |
| Dev / GitHub | [coroot/coroot](https://github.com/coroot/coroot) | GitHub MCP | real open-source observability tool, accessed read-only via MCP server. |

## Knowledge representation

Each domain keeps its own representation -- there's no shared schema or
entity graph linking them, by design (domains are disjoint, see "Why
langgraph over A2A" above).

| Domain | Representation | Why |
|---|---|---|
| HR handbook | Chunked text + pgvector embeddings (`hr_documents` table) | Handbook content is unstructured prose; semantic similarity search is the natural fit, so it's embedded once at ingestion time and retrieved by vector distance. |
| Sales | Normalized relational rows (Northwind schema, Postgres) | Already structured, queryable data -- text2SQL introspects the live schema at query time rather than keeping a separate model of it. |
| Dev / GitHub | Raw commit metadata, fetched live, never stored | No representation to maintain at all -- the MCP tool call returns commits straight to the LLM for summarization, so there's nothing to keep in sync. |

## Agent access / permission control

1. user permission control

To demostrate the availablity for access control, I've setup role mechanism, it comes from the `users` table (created from`postgres/init/init.sql`), looked up
via `GET /access?username=...` and enforced server-side in every `/chat` call.

| Role | Login | hr_rag | sales_sql | github |
|---|---|---|---|---|
| admin | Hsuan AD | ✅ | ✅ | ✅ |
| user | Hsuan US | ✅ | ❌ | ❌ |
| dev | Hsuan DE | ✅ | ✅ | ✅ |
| sales | Hsuan SA | ✅ | ✅ | ❌ |

2. Agent query control: app level

  * Sales agent: there's a _validate() function to inforced blocking non SELECT queries, also this agent is bound to `sales_readonly` role
  * HR RAG agent: only retrieval interation with DB
  * GitHub MCP agent: it's control by the read-only PAT


## Data pipeline maintainence

**Update pipeline**: current setup there's only HR documentation need to be updated, *assume the data is hosted in github readme*. Either we can create a job or API call add to github action once there's a changes it would trigger the job. Or we can setup a daily/weekly scheduler to check for the update.

**Clean upsert**: in HR doc, the unique document key is the url (related path on repo), I use this to identify modified documents, and delete related chunks from vector db and reindex the new and updated ones.

**Other agents**:

* for sales agents, text2SQL generally need regular revisit with business stakeholder to update the search intent but it's not implemented for this demo.
* for github MCP no data storage needed.


## Chunking strategy

1. why chunk 1024? it's a common default RAG chunking, and `lama3.2:1b` perform more stable within 4000-5000 token, retrieving `top_k=3` adding system prompt this fit well with the context.
2. Table-aware chunking: markdown tables are detected and reserved, since splitting a table across chunks is a common text-chunking failure that loses context on retrieval.
3. overlap 200 token: generally speaking a paragrah is around 150-200 token, by doing so we are less likely to loss information


## Trade-offs design:

1. Smaller-model -> open source and local laptop resource limitation.
2. Github MCP hardcode limit -> limit the max_comment and timeout second, all these approach is for demo purpose to reduce context length.
3. Adding keyword detection to skip routing classifier part -> it is dangerous approach, but it's to speed up some process, future better have a intent table to support this steps.
4. Hardcode sales schema for text2sql-> work fine with small dataset, but need a more sophisticate design for this part.
5. Not implemented follow up question-> due to the time for implementation, it can be future options, which need to align the cache logic with business concept.


## Local Setup

Copy `.env.example` to `.env` and fill in your own `GITHUB_PERSONAL_ACCESS_TOKEN`. (A fine-grained PAT with no repositories
selected and read-only access is enough);

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
----------------------------
## How AI is used in this project

My AI-SDLC for this project: Plan → Draft → Review/Challenge → Test → Document → Validate.

1. **Plan**: As a senior AI engineer, I've first comeup with the project architecture in my mind. First knowing exactly what component and detail setup in my mind.
2. **Draft**: Feed the prompt with claude on my idea and my code example (private side project) to first draft a whole project.
3. **Review/Challenge**: Checking code by code if anything is missing from my past experience (like code review), challenge the method AI is providing. e.g. Claude's first draft skipped FastAPI's own recommended `Depends(get_db)` session lifecycle, using raw `SessionLocal()` calls instead, caught and adjusted by me.
4. **Test**: Asking Claude generating and iterating on the tests/ suite (RBAC, router classification edge cases, SQL-injection guardrails, GitHub agent timeout/error paths). Back and forth human testing in the loop to adjust the resources and suitable setup for the POC.
5. **Document**: Once tested and satisfy with the result I've asked AI to generate google recommended style of comment for each function; from claude generated readme adjust with my own word and my own thought / document order etc...
6. **Validate**: Finally ask AI to check if I meet all the aspect of the project


-----------------------------
## Future trouble shooting

Once I get the feeback from the log, or a human feedback, there are few steps to take.

1. Human / agent classify the feedback
2. Check which component cause issue, we can identify it from the log and reasoning.
  * router: prompt adjust, agent description adjust etc...
  * HR_rag: can the issue be fixed from the prompt or the issue is from retrieval


More over we should continuously monitoring, latency, periodically resample recent data to run evaluation metrics (llm as a judge etc...)
