"""ContentProtector の protect/restore 対称性テスト"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.protection.protector import ContentProtector


def _roundtrip(text, glossary=None):
    """protect → (翻訳せず) → restore して元に戻るか確認"""
    p = ContentProtector(glossary or {})
    protected = p.protect(text)
    restored = p.restore(protected)
    p.clear()
    return protected, restored


def test_citation_roundtrip():
    text = "As shown in [1] and [2, 3], the result holds."
    protected, restored = _roundtrip(text)
    # 引用がプレースホルダ化されている
    assert "[1]" not in protected
    # 復元で元に戻る
    assert restored == text


def test_reference_roundtrip():
    text = "See Figure 3 and Table 2 for details."
    protected, restored = _roundtrip(text)
    assert "Figure 3" not in protected
    assert restored == text


def test_display_math_roundtrip():
    text = "The loss is $$L = \\sum_i (y_i - x_i)^2$$ here."
    protected, restored = _roundtrip(text)
    assert "$$" not in protected
    assert restored == text


def test_currency_not_protected():
    """通貨記号は数式として誤検知されない"""
    text = "The item costs $5.99 per unit."
    p = ContentProtector({})
    protected = p.protect(text)
    p.clear()
    # $5.99 が数式プレースホルダになっていない（金額がそのまま残る）
    assert "5.99" in protected


def test_glossary_term_roundtrip():
    glossary = {"machine learning": "機械学習"}
    text = "We use machine learning techniques."
    p = ContentProtector(glossary)
    protected = p.protect(text)
    # 用語がプレースホルダ化
    assert "machine learning" not in protected
    # 復元すると日本語訳になる
    restored = p.restore(protected)
    p.clear()
    assert "機械学習" in restored


def test_symbol_term_matches():
    """記号を含む用語（C++ など）もマッチする"""
    glossary = {"C++": "C++"}
    text = "We implemented it in C++ for speed."
    p = ContentProtector(glossary)
    protected = p.protect(text)
    p.clear()
    assert "C++" not in protected or "⟦" in protected


def test_empty_text():
    protected, restored = _roundtrip("")
    assert restored == ""


def test_no_protection_needed():
    text = "This is plain text without anything special."
    protected, restored = _roundtrip(text)
    assert restored == text


def test_placeholder_is_ascii():
    """プレースホルダが純粋なASCII（DeepLが変換しない形式）であること"""
    import re
    p = ContentProtector({"machine learning": "機械学習"})
    protected = p.protect("We use machine learning and [1] and Figure 3.")
    p.clear()
    phs = re.findall(r'XQX[A-Z]+Q\d+QXQ', protected)
    assert len(phs) >= 3
    # すべてASCII
    for ph in phs:
        assert all(ord(c) < 128 for c in ph)


def test_placeholder_no_unicode_brackets():
    """旧形式のUnicode囲み文字⟦⟧を使っていないこと"""
    p = ContentProtector({})
    protected = p.protect("See [1] and Figure 2.")
    p.clear()
    assert "⟦" not in protected
    assert "⟧" not in protected


def test_restore_tolerates_spaces():
    """プレースホルダに空白が混入しても復元できる"""
    p = ContentProtector({"SAT": "充足可能性判定問題"})
    protected = p.protect("We use SAT here.")
    # 翻訳エンジンが空白を挿入したと仮定
    import re
    ph = re.findall(r'XQX[A-Z]+Q\d+QXQ', protected)[0]
    spaced = " ".join(ph)  # 1文字ずつ空白
    deformed = protected.replace(ph, spaced)
    restored = p.restore(deformed)
    p.clear()
    assert "充足可能性判定問題" in restored


def test_restore_tolerates_lowercase():
    """プレースホルダが小文字化しても復元できる"""
    p = ContentProtector({"SAT": "充足可能性判定問題"})
    protected = p.protect("We use SAT here.")
    import re
    ph = re.findall(r'XQX[A-Z]+Q\d+QXQ', protected)[0]
    deformed = protected.replace(ph, ph.lower())
    restored = p.restore(deformed)
    p.clear()
    assert "充足可能性判定問題" in restored
