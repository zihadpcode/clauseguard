"""Turns an uploaded file into plan text. Plain text is the guaranteed path;
digitally generated PDF is best effort (scanned PDFs have no text layer)."""
import io
from dataclasses import dataclass

MAX_BYTES = 5 * 1024 * 1024
MAX_PDF_PAGES = 60


class IngestError(ValueError):
    pass


@dataclass
class Extracted:
    text: str
    source: str


def extract(filename: str, data: bytes) -> Extracted:
    if len(data) > MAX_BYTES:
        raise IngestError(f"{filename} is larger than {MAX_BYTES // (1024 * 1024)} MB.")
    name = filename.lower()
    if name.endswith(".txt"):
        return Extracted(_decode_text(data), f"upload: {filename}")
    if name.endswith(".pdf"):
        return _extract_pdf(filename, data)
    raise IngestError("Only .txt and digitally generated .pdf files are supported.")


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _extract_pdf(filename: str, data: bytes) -> Extracted:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(io.BytesIO(data))
        pages = reader.pages
        if len(pages) > MAX_PDF_PAGES:
            raise IngestError(f"{filename} has {len(pages)} pages; the limit is {MAX_PDF_PAGES}.")
        text = "\n\n".join((p.extract_text() or "").strip() for p in pages).strip()
    except PdfReadError as e:
        raise IngestError(f"{filename} could not be read as a PDF ({e}).") from e
    if not text:
        raise IngestError(
            f"{filename} has no extractable text. Scanned or image-only PDFs are not "
            "supported; paste the plan text instead."
        )
    plural = "s" if len(pages) != 1 else ""
    return Extracted(text, f"upload: {filename} ({len(pages)} page{plural}, PDF text layer)")
