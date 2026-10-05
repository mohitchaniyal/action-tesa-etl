from pathlib import Path

from sqlalchemy.orm import Session

from action_tesa_etl.core.invoice_extractor import extract_invoice
from action_tesa_etl.db import init_db, make_engine, session_factory
from action_tesa_etl.ingestor.loader import invoice_from_frames, replace_invoice
import argparse
from loguru import logger

LOCAL_SOURCE = "local"


class IngestorService:
    def __init__(
        self,
        source: str,
        path: str | None = None,
        database_url: str | None = None,
    ):
        if source != LOCAL_SOURCE:
            raise NotImplementedError(
                f"source {source!r} is not supported yet; use {LOCAL_SOURCE!r}"
            )
        self.source = source
        self.path = path
        self.database_url = database_url

    def read_files_from_path(self) -> list[Path]:
        logger.info(f"Reading files from path: {self.path}")
        if not self.path:
            raise ValueError("path is required")

        root = Path(self.path)
        if not root.exists():
            raise FileNotFoundError(self.path)

        if root.is_file():
            if root.suffix.lower() != ".pdf":
                raise ValueError(f"{root} is not a PDF")
            return [root]

        pdfs = sorted(
            file
            for file in root.iterdir()
            if file.is_file() and file.suffix.lower() == ".pdf"
        )
        logger.info(f"Found {len(pdfs)} PDF files in {root}")
        return pdfs

    def ingest(self) -> list[str]:
        logger.info(f"Ingesting invoices from {self.path}")
        pdfs = self.read_files_from_path()
        engine = make_engine(self.database_url)
        init_db(engine)
        factory = session_factory(engine)
        loaded: list[str] = []
        failed: list[str] = []

        with factory() as session:
            for pdf in pdfs:
                try:
                    loaded.append(self._load_pdf(session, pdf))
                    session.commit()
                except Exception:
                    session.rollback()
                    failed.append(pdf.name)
                    logger.exception(f"Failed to ingest {pdf}")

        logger.info(f"Ingested {len(loaded)} invoices")
        if failed:
            raise RuntimeError(
                f"Failed to ingest {len(failed)} invoices: {', '.join(failed)}"
            )
        return loaded

    def _load_pdf(self, session: Session, pdf: Path) -> str:
        logger.info(f"Loading PDF: {pdf}")
        frames = extract_invoice(str(pdf))
        header = invoice_from_frames(frames)
        replace_invoice(session, header)
        logger.info(f"Replaced invoice: {header.invoice_no}")
        return header.invoice_no

def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest invoices from a local path")
    parser.add_argument("--path", type=str, required=True, help="Path to the invoices")
    args = parser.parse_args()
    IngestorService(source=LOCAL_SOURCE, path=args.path).ingest()


if __name__ == "__main__":
    main()
