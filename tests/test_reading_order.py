"""読み順ソートと2段組み検出のテスト"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parser.pdf_document import (
    Block, BlockType, BoundingBox, Style,
    calculate_reading_order, merge_adjacent_blocks,
)


def _block(x0, y0, x1, y1, text="", font_size=10.0):
    return Block(
        id="", type=BlockType.PARAGRAPH,
        bbox=BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1),
        content=text,
        style=Style(font_name="", font_size=font_size),
    )


def test_single_column_order():
    """1段組みは y0 昇順"""
    blocks = [
        _block(50, 300, 560, 320, "C"),
        _block(50, 100, 560, 120, "A"),
        _block(50, 200, 560, 220, "B"),
    ]
    result = calculate_reading_order(blocks)
    assert [b.content for b in result] == ["A", "B", "C"]


def test_two_column_order():
    """2段組みは左段を上から下→右段を上から下"""
    blocks = [
        # 左段
        _block(50, 100, 280, 120, "L1"),
        _block(50, 200, 280, 220, "L2"),
        # 右段
        _block(320, 80, 560, 100, "R1"),
        _block(320, 180, 560, 200, "R2"),
    ]
    result = calculate_reading_order(blocks)
    assert [b.content for b in result] == ["L1", "L2", "R1", "R2"]


def test_merge_adjacent_same_paragraph():
    """フォント・位置が近い連続ブロックは結合される"""
    blocks = [
        _block(50, 100, 560, 112, "first line", font_size=10.0),
        _block(50, 114, 560, 126, "second line", font_size=10.0),
    ]
    merged = merge_adjacent_blocks(blocks)
    assert len(merged) == 1
    assert "first line second line" == merged[0].content


def test_merge_different_font_not_merged():
    """フォントサイズが大きく違うと結合されない（見出しと本文）"""
    blocks = [
        _block(50, 100, 560, 120, "Heading", font_size=16.0),
        _block(50, 122, 560, 134, "body text", font_size=10.0),
    ]
    merged = merge_adjacent_blocks(blocks)
    assert len(merged) == 2


def test_merge_hyphenation():
    """行末ハイフンは連結される"""
    blocks = [
        _block(50, 100, 560, 112, "inter-", font_size=10.0),
        _block(50, 114, 560, 126, "connected", font_size=10.0),
    ]
    merged = merge_adjacent_blocks(blocks)
    assert merged[0].content == "interconnected"


def test_empty_blocks():
    assert calculate_reading_order([]) == []
    assert merge_adjacent_blocks([]) == []
