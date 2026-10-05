# Action Tesa ETL

Reads invoice PDFs from a local folder, stores them in a database, and serves them as JSON.

Requires Python 3.14 and [uv](https://docs.astral.sh/uv/).

## Setup

From the project root:

```bash
uv sync
cp .env.example .env
```

`.env` controls the database and the API address:

```
DATABASE_URL=sqlite:///data/invoices.db
EXPOSOR_HOST=127.0.0.1
EXPOSOR_PORT=8000
```

`sqlite:///data/invoices.db` is created on the first run. To use Postgres instead, point `DATABASE_URL` at that database. The same URL is used by the ingestor and the exposor.

```
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/invoices
```

## Ingestor

Loads every PDF in a folder into the database. Re-running an invoice replaces that invoice.

```bash
uv run action-tesa-etl --path "/path/to/invoices"
```

`--path` can also be a single PDF file. Quote the path when it contains spaces.

Each invoice is saved as soon as it loads. If one PDF fails, the invoices already saved stay in the database and the command exits with an error.

## Exposor

Serves the stored invoices over HTTP.

```bash
uv run action-tesa-exposor
```

The API listens on `http://127.0.0.1:8000` unless `EXPOSOR_HOST` or `EXPOSOR_PORT` is changed. Interactive docs are at `http://127.0.0.1:8000/docs`.

`GET /invoices` returns a list. Each item is one invoice:

```json
{
  "header": {},
  "items": [],
  "summary": []
}
```

Optional filters are `invoice_no` and `date_of_issue`. Pass both to require a match on each. `date_of_issue` uses the stored date, for example `2023-07-03`.

```bash
curl "http://127.0.0.1:8000/invoices"
curl "http://127.0.0.1:8000/invoices?invoice_no=51109301"
curl "http://127.0.0.1:8000/invoices?date_of_issue=2023-07-03"
```
