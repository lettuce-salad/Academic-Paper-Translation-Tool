"""JSON シリアライズ往復テスト（figures/tables/caption が消えないか）"""
import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parser.pdf_document import (
    PDFDocument, Page, Block, Figure, Table,
    BlockType, BoundingBox, Style,
)


def _make_doc():
    doc = PDFDocument(metadata={"title": "Test Paper"})
    page = Page(number=1, width=612, height=792)

    page.add_block(Block(
        id="b1", type=BlockType.PARAGRAPH,
        bbox=BoundingBox(x0=50, y0=100, x1=560, y1=120),
        content="Body text.",
        style=Style(font_name="Times", font_size=10.0),
    ))

    cap = Block(
        id="cap1", type=BlockType.CAPTION,
        bbox=BoundingBox(x0=50, y0=300, x1=560, y1=320),
        content="Figure 1. Example.",
        style=Style(font_name="Times", font_size=9.0),
    )
    page.add_figure(Figure(
        id="fig1",
        bbox=BoundingBox(x0=50, y0=200, x1=300, y1=300),
        image_data=b"",
        caption=cap,
    ))
    page.add_table(Table(
        id="tbl1",
        bbox=BoundingBox(x0=50, y0=400, x1=300, y1=500),
        rows=2, cols=2, cells=[],
    ))
    doc.add_page(page)
    return doc


def test_json_roundtrip_preserves_figures_tables():
    doc = _make_doc()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        path = f.name
    doc.to_json(path)

    loaded = PDFDocument.from_json(path)
    Path(path).unlink()

    page = loaded.pages[0]
    assert len(page.figures) == 1, "figure が復元されていない"
    assert len(page.tables) == 1, "table が復元されていない"


def test_json_roundtrip_preserves_caption():
    doc = _make_doc()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        path = f.name
    doc.to_json(path)

    loaded = PDFDocument.from_json(path)
    Path(path).unlink()

    fig = loaded.pages[0].figures[0]
    assert fig.caption is not None, "figure caption が復元されていない"
    assert "Figure 1" in fig.caption.content


def test_json_roundtrip_metadata():
    doc = _make_doc()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        path = f.name
    doc.to_json(path)
    loaded = PDFDocument.from_json(path)
    Path(path).unlink()
    assert loaded.metadata.get("title") == "Test Paper"
