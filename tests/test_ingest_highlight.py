import pytest

from clauseguard import highlight, ingest


def _pdf(page_streams: list[str]) -> bytes:
    """Minimal valid PDF; each stream is raw page content (may be empty)."""
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", None,
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    kids = []
    for stream in page_streams:
        content_id = len(objs) + 2
        page_id = len(objs) + 1
        kids.append(f"{page_id} 0 R")
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                    f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>")
        objs.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
    objs[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>"
    out, offsets = "%PDF-1.4\n", []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out.encode("latin-1")))
        out += f"{i} 0 obj\n{body}\nendobj\n"
    xref = len(out.encode("latin-1"))
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n"
    out += "".join(f"{o:010d} 00000 n \n" for o in offsets)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    return out.encode("latin-1")


def _text_stream(*lines):
    ops = ["BT /F1 11 Tf 72 720 Td 14 TL"]
    ops += [f"({line}) Tj T*" for line in lines]
    ops.append("ET")
    return "\n".join(ops)


def test_txt_upload_decodes_utf8_with_bom():
    data = "﻿Harnesses will be inspected prior to each use.".encode("utf-8")
    out = ingest.extract("plan.txt", data)
    assert out.text == "Harnesses will be inspected prior to each use."
    assert out.source == "upload: plan.txt"


def test_txt_upload_falls_back_to_cp1252():
    out = ingest.extract("plan.txt", "Coordinator’s log".encode("cp1252"))
    assert out.text == "Coordinator’s log"


def test_digital_pdf_text_layer_is_extracted():
    data = _pdf([_text_stream("Harnesses and lanyards will be inspected monthly.",
                              "Training certification records are maintained by the HR office.")])
    out = ingest.extract("plan.pdf", data)
    assert "inspected monthly" in out.text
    assert "HR office" in out.text
    assert "1 page" in out.source


def test_scanned_pdf_without_text_layer_is_refused():
    with pytest.raises(ingest.IngestError, match="no extractable text"):
        ingest.extract("scan.pdf", _pdf([""]))


def test_corrupt_pdf_is_refused():
    with pytest.raises(ingest.IngestError):
        ingest.extract("broken.pdf", b"%PDF-1.4 not really a pdf")


def test_unsupported_extension_is_refused():
    with pytest.raises(ingest.IngestError, match="Only .txt"):
        ingest.extract("plan.docx", b"PK...")


def test_oversized_upload_is_refused():
    with pytest.raises(ingest.IngestError, match="larger than"):
        ingest.extract("plan.txt", b"x" * (ingest.MAX_BYTES + 1))


PLAN = "Rescue is immediate.\nHarnesses will be inspected\nmonthly by the coordinator’s team.\nEnd."


def test_highlight_finds_span_across_line_break_and_curly_quote():
    spans = [("PFAS_INSPECT_01", "potential_conflict",
              "Harnesses will be inspected monthly by the coordinator's team.")]
    found = highlight.find_spans(PLAN, spans)
    assert len(found) == 1
    start, end, check_id, _ = found[0]
    assert PLAN[start:end].startswith("Harnesses") and PLAN[start:end].endswith("team.")


def test_highlight_skips_unplaceable_and_overlapping_spans():
    spans = [
        ("A", "evidence_found", "Harnesses will be inspected"),
        ("B", "evidence_found", "will be inspected monthly"),
        ("C", "evidence_found", "never appears in the plan"),
    ]
    found = highlight.find_spans(PLAN, spans)
    assert [f[2] for f in found] == ["A"]


def test_highlight_html_escapes_plan_text():
    out = highlight.highlight_html("<b>bold</b> Rescue is immediate.", [("PFAS_RESCUE_01", "evidence_found", "Rescue is immediate.")])
    assert "&lt;b&gt;bold&lt;/b&gt;" in out
    assert '<mark class="cg-hl cg-hl--evidence_found"' in out
    assert ">RESCUE</sup>" in out
