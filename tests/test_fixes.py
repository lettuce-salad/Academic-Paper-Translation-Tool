"""今回の修正（段組み判定・数式保護・参照バリアント）の回帰テスト"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parser.pdf_document import (
    Block, BlockType, BoundingBox, Style, calculate_reading_order,
)
from src.protection.protector import ContentProtector


def _block(x0, y0, x1, y1, text=""):
    return Block(
        id="", type=BlockType.PARAGRAPH,
        bbox=BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1),
        content=text,
        style=Style(font_name="", font_size=10.0),
    )


# --- 修正1: 1段組み中央配置を誤判定しない ---

def test_single_column_center_not_misdetected():
    """中央に集中する1段組みが2段組み誤判定されない"""
    blocks = [_block(150, 100 + i * 20, 450, 115 + i * 20, f"L{i}") for i in range(10)]
    result = calculate_reading_order(blocks)
    assert [b.content for b in result] == [f"L{i}" for i in range(10)]


def test_two_column_still_detected():
    """正しい2段組みは引き続き検出される"""
    blocks = []
    for i in range(5):
        blocks.append(_block(50, 100 + i * 20, 280, 115 + i * 20, f"L{i}"))
    for i in range(5):
        blocks.append(_block(320, 100 + i * 20, 560, 115 + i * 20, f"R{i}"))
    result = calculate_reading_order(blocks)
    expected = [f"L{i}" for i in range(5)] + [f"R{i}" for i in range(5)]
    assert [b.content for b in result] == expected


# --- 修正2: Unicode数学記号の保護 ---

def test_unicode_math_protected():
    p = ContentProtector({})
    text = "where α ≤ β holds"
    protected = p.protect(text)
    restored = p.restore(protected)
    p.clear()
    assert "α" not in protected  # 保護された
    assert restored == text       # 復元できる


def test_plain_text_not_over_protected():
    """数学記号のない通常英文は過剰保護されない"""
    p = ContentProtector({})
    text = "the value of x is 5"
    protected = p.protect(text)
    p.clear()
    # 通常の単語が残っている
    assert "value" in protected and "is" in protected


# --- 修正: 引用バリアント ---

def test_two_author_citation():
    p = ContentProtector({})
    text = "As shown by (Smith and Jones, 2020), this works."
    protected = p.protect(text)
    restored = p.restore(protected)
    p.clear()
    assert "(Smith and Jones, 2020)" not in protected
    assert restored == text


def test_reference_decimal_number():
    """Eq. (5.2) のような小数点番号も保護"""
    p = ContentProtector({})
    text = "See Equation 5.2 for the derivation."
    protected = p.protect(text)
    restored = p.restore(protected)
    p.clear()
    assert "Equation 5.2" not in protected
    assert restored == text


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✅ {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
