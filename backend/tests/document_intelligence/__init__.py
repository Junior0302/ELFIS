"""Helpers tests Document Intelligence."""

from __future__ import annotations

import io
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models_saas  # noqa: F401
from app.ai import ai_models  # noqa: F401
from app.database import Base
from app.document_intelligence import document_models  # noqa: F401
from app.document_intelligence.document_registry import bootstrap_extractors
from app.events import event_models  # noqa: F401
from app.jobs import bootstrap_job_handlers, job_models  # noqa: F401
from app.models_saas import Organization, User
from app.models_vault import VaultDocument


def make_text_pdf(text: str = "Facture FAC-1 Montant HT 100 TVA 20 TTC 120") -> bytes:
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, NumberObject

    # PDF minimal avec texte via page blank + annotation n'est pas fiable ;
    # on utilise reportlab si dispo, sinon pypdf + page content stream simple.
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter

        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        y = 750
        for line in text.split("\n"):
            c.drawString(72, y, line[:100])
            y -= 14
        c.save()
        return buf.getvalue()
    except ImportError:
        pass

    # Fallback : PDF 1.4 minimal avec un flux texte
    content = f"BT /F1 12 Tf 72 720 Td ({text[:80]}) Tj ET".encode("latin-1", errors="replace")
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    # Inject stream manually
    stream = DecodedStreamObject()
    stream.set_data(content)
    page[NameObject("/Contents")] = stream
    resources = DictionaryObject()
    font = DictionaryObject()
    font[NameObject("/Type")] = NameObject("/Font")
    font[NameObject("/Subtype")] = NameObject("/Type1")
    font[NameObject("/BaseFont")] = NameObject("/Helvetica")
    resources[NameObject("/Font")] = DictionaryObject({NameObject("/F1"): font})
    page[NameObject("/Resources")] = resources
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def make_empty_pdf() -> bytes:
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def setup_di_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(Organization(id=1, name="Org1"))
    db.add(Organization(id=2, name="Org2"))
    db.add(User(id=1, email="a@b.c", first_name="A", last_name="B", password_hash="x"))
    db.add(
        VaultDocument(
            id="vd-1",
            organization_id=1,
            document_type="supplier_invoice",
            original_filename="facture.pdf",
            storage_path="org/1/facture.pdf",
            mime_type="application/pdf",
            file_size=1000,
            checksum_sha256="abc",
            archive_status="archived",
            version=1,
        )
    )
    db.add(
        VaultDocument(
            id="vd-txt",
            organization_id=1,
            document_type="other",
            original_filename="notes.txt",
            storage_path="org/1/notes.txt",
            mime_type="text/plain",
            file_size=100,
            checksum_sha256="def",
            archive_status="archived",
            version=1,
        )
    )
    db.commit()
    bootstrap_extractors()
    bootstrap_job_handlers()
    return db, Session, engine
