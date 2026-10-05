from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.orm import Session

from action_tesa_etl.config import settings
from action_tesa_etl.db import init_db, make_engine, session_factory
from action_tesa_etl.exposor.service import find_invoices, invoice_to_dict


def create_app(database_url: str | None = None) -> FastAPI:
    engine = make_engine(database_url)
    init_db(engine)
    factory = session_factory(engine)

    app = FastAPI(title="Action Tesa Invoice Exposor")

    def get_session():
        with factory() as session:
            yield session

    @app.get("/invoices")
    def list_invoices(
        invoice_no: str | None = Query(default=None),
        date_of_issue: str | None = Query(default=None),
        session: Session = Depends(get_session),
    ) -> list[dict]:
        invoices = find_invoices(
            session,
            invoice_no=invoice_no,
            date_of_issue=date_of_issue,
        )
        return [invoice_to_dict(invoice) for invoice in invoices]

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run(app, host=settings.exposor_host, port=settings.exposor_port)
