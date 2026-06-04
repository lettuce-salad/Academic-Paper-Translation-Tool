"""
Content Protector
翻訳禁止領域を保護するシステム（Unicode記法）
"""
import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class ProtectionType(Enum):
    """保護タイプ"""
    MATH = "MATH"        # 数式: $...$, $$...$$
    CODE = "CODE"        # コード: `...`, ```...```
    REF = "REF"          # 参照: Figure 3, Eq. (5)
    CITE = "CITE"        # 引用: [1], [2]
    URL = "URL"          # URL
    LATEX = "LATEX"      # LaTeXコマンド
    TERM = "TERM"        # 専門用語


@dataclass
class ProtectedItem:
    """保護されたアイテム"""
    type: ProtectionType
    placeholder: str
    original: str
    replacement: Optional[str] = None  # 復元時の置換テキスト（専門用語の場合）


class ContentProtector:
    """
    翻訳禁止領域を保護

    プレースホルダは翻訳エンジン（特にDeepL）が別文字に変換しない形式を使う。
    Unicode囲み文字（⟦⟧）はDeepLが視覚的に似た記号に変換してしまうため、
    純粋なASCII英大文字列「XNODONXNN」形式を採用する。
    （X+3文字タイプ識別 + 4桁番号 + 区切り、すべて A-Z0-9）
    """

    # 例: XQXTERMQ0005  （XQX...Q が境界、TERM がタイプ、0005 が番号）
    # 翻訳エンジンが分割・小文字化しても復元できるよう、復元側は緩いパターンで拾う。
    PLACEHOLDER_TEMPLATE = "XQX{type}Q{index:04d}QXQ"

    def __init__(self, glossary: Optional[Dict[str, str]] = None):
        """
        Args:
            glossary: 専門用語辞書 {英語: 日本語}
        """
        self.glossary = glossary or {}
        self.protected_items: List[ProtectedItem] = []
        self.counters: Dict[str, int] = {}
    
    def protect(self, text: str) -> str:
        """
        テキスト内の保護対象をプレースホルダに置換
        
        Args:
            text: 元のテキスト
            
        Returns:
            保護されたテキスト
        """
        self.protected_items = []
        self.counters = {}
        
        protected_text = text
        
        # 保護の順序（重要: 長いものから先に、重なりを防ぐ）
        protected_text = self._protect_latex_commands(protected_text)
        protected_text = self._protect_display_math(protected_text)
        protected_text = self._protect_inline_math(protected_text)
        protected_text = self._protect_unicode_math(protected_text)
        protected_text = self._protect_code_blocks(protected_text)
        protected_text = self._protect_inline_code(protected_text)
        protected_text = self._protect_references(protected_text)
        protected_text = self._protect_citations(protected_text)
        protected_text = self._protect_urls(protected_text)
        protected_text = self._protect_terms(protected_text)
        
        return protected_text
    
    def restore(self, text: str) -> str:
        """
        プレースホルダを元の内容に復元。

        翻訳エンジンがプレースホルダに軽微な変形を加える場合
        （大文字小文字の変化、文字間への空白挿入）にも対応するため、
        まず厳密一致で置換し、残ったものを緩い正規表現で拾う。
        """
        restored_text = text

        # 1. 厳密一致で置換（逆順：後から保護したものから）
        for item in reversed(self.protected_items):
            replacement = item.replacement if item.replacement else item.original
            restored_text = restored_text.replace(item.placeholder, replacement)

        # 2. 変形したプレースホルダを緩いパターンで拾う
        #    XQX TERM Q 0005 QXQ が空白混入・小文字化していても復元
        for item in reversed(self.protected_items):
            # placeholder から type と index を抽出
            m = re.match(r'XQX([A-Z]+)Q(\d+)QXQ', item.placeholder)
            if not m:
                continue
            type_name, index = m.group(1), m.group(2)
            replacement = item.replacement if item.replacement else item.original

            # 各文字の間に空白が入りうる、大文字小文字問わずのパターン
            loose = (
                r'X\s*Q\s*X\s*'
                + r'\s*'.join(type_name)
                + r'\s*Q\s*'
                + r'\s*'.join(index)
                + r'\s*Q\s*X\s*Q'
            )
            restored_text = re.sub(loose, lambda _: replacement,
                                   restored_text, flags=re.IGNORECASE)

        return restored_text
    
    def _make_placeholder(self, ptype: ProtectionType) -> str:
        """プレースホルダを生成"""
        type_name = ptype.value
        
        if type_name not in self.counters:
            self.counters[type_name] = 0
        
        index = self.counters[type_name]
        self.counters[type_name] += 1
        
        return self.PLACEHOLDER_TEMPLATE.format(type=type_name, index=index)
    
    def _protect_pattern(self, text: str, pattern: str, ptype: ProtectionType, 
                        flags: int = 0) -> str:
        """
        正規表現パターンでマッチした部分を保護
        
        Args:
            text: テキスト
            pattern: 正規表現パターン
            ptype: 保護タイプ
            flags: 正規表現フラグ
            
        Returns:
            保護されたテキスト
        """
        regex = re.compile(pattern, flags)
        
        def replacer(match):
            original = match.group(0)
            placeholder = self._make_placeholder(ptype)
            
            item = ProtectedItem(
                type=ptype,
                placeholder=placeholder,
                original=original
            )
            
            self.protected_items.append(item)
            return placeholder
        
        return regex.sub(replacer, text)
    
    def _protect_latex_commands(self, text: str) -> str:
        """LaTeXコマンドを保護。ネストした {} も扱える簡易実装。"""
        # \command の後の {} グループをまとめて保護
        # ネスト1段まで対応: \frac{...}{...} など
        pattern = r'\\[a-zA-Z]+(?:\{[^{}]*(?:\{[^{}]*\}[^{}]*)?\})*'
        return self._protect_pattern(text, pattern, ProtectionType.LATEX)
    
    def _protect_display_math(self, text: str) -> str:
        """ディスプレイ数式を保護: $$...$$"""
        pattern = r'\$\$.+?\$\$'   # 非貪欲で内部の $ も許容
        return self._protect_pattern(text, pattern, ProtectionType.MATH, re.DOTALL)

    def _protect_inline_math(self, text: str) -> str:
        """
        インライン数式を保護: $...$

        通貨記号の誤検知を防ぐため、開き $ の直後が数字＋空白パターン
        （$5.99 など）でないこと、かつ内部に数式記号を含むことを条件にする。
        具体的には「$ の直後が空白でない」「閉じ $ の直前が空白でない」
        という LaTeX インライン数式の慣習に従う。
        """
        # $（直後非空白・非数字始まりの通貨を除外）...（直前非空白）$
        pattern = r'(?<![\d$])\$(?!\s)(?:[^$\n]*[^\s$])?\$(?![\d])'
        return self._protect_pattern(text, pattern, ProtectionType.MATH)

    def _protect_unicode_math(self, text: str) -> str:
        """
        PDFから抽出された数式を保護する。

        LaTeX原稿と違い、PDFのテキスト抽出結果には $...$ が存在せず、
        数式は Unicode の数学記号（ギリシャ文字・演算子）として現れる。
        これらの記号と、それに隣接する変数・数字・添字を一塊で保護する。

        例:
            "where α ≤ β"        → α ≤ β を保護
            "the integral ∫f(x)dx" → ∫f(x)dx を保護
        """
        # 数学記号の文字クラス
        math_sym = (
            r'∑∏∫∂∇≤≥≠±×÷√∞∈∉⊂⊃⊆⊇∩∪∀∃¬∧∨⊕⊗→←↔↦⇒⇔'
            r'αβγδεζηθικλμνξοπρστυφχψω'
            r'ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ'
            r'≈≅≡≪≫⌊⌋⌈⌉∥∝∅ℵ'
        )
        # 数学記号を含み、その周辺の英数字・添字・括弧・記号を巻き込んだ連続塊
        # 例: ∫f(x)dx, α≤β, x_i^2 （上付き下付きの Unicode 含む）
        pattern = (
            r'[A-Za-z0-9_\^\(\)\[\]\{\}\.,\-+/=]*'
            r'[' + math_sym + r']'
            r'[A-Za-z0-9_\^\(\)\[\]\{\}\.,\-+/=' + math_sym + r'\s]*'
            r'[' + math_sym + r'A-Za-z0-9\)\]\}]'
            r'|[' + math_sym + r']'
        )
        return self._protect_pattern(text, pattern, ProtectionType.MATH)
    
    def _protect_code_blocks(self, text: str) -> str:
        """コードブロックを保護: ```...```"""
        pattern = r'```[^`]+```'
        return self._protect_pattern(text, pattern, ProtectionType.CODE, re.DOTALL)
    
    def _protect_inline_code(self, text: str) -> str:
        """インラインコードを保護: `...`"""
        pattern = r'`[^`\n]+`'
        return self._protect_pattern(text, pattern, ProtectionType.CODE)
    
    def _protect_references(self, text: str) -> str:
        """参照を保護"""
        patterns = [
            r'Figures?\s+\d+(?:\.\d+)*',
            r'Figs?\.\s*\d+(?:\.\d+)*',
            r'Tables?\s+\d+(?:\.\d+)*',
            r'Tabs?\.\s*\d+(?:\.\d+)*',
            r'Equations?\s+\d+(?:\.\d+)*',
            r'Eqn?s?\.\s*\(?\d+(?:\.\d+)*\)?',   # Eq. (5), Eqn 5, Eqs. 3
            r'Sections?\s+\d+(?:\.\d+)*',
            r'Secs?\.\s*\d+(?:\.\d+)*',
            r'Algorithms?\s+\d+',
            r'Listings?\s+\d+',
            r'Theorems?\s+\d+',
            r'Lemmas?\s+\d+',
            r'Corollary\s+\d+',
            r'Propositions?\s+\d+',
            r'Definitions?\s+\d+',
            r'Appendix\s+[A-Z\d]+',
        ]
        
        for pattern in patterns:
            text = self._protect_pattern(text, pattern, ProtectionType.REF, re.IGNORECASE)
        
        return text
    
    def _protect_citations(self, text: str) -> str:
        """引用を保護"""
        patterns = [
            r'\[\d+\]',                                          # [1]
            r'\[\d+\s*-\s*\d+\]',                               # [3-5]
            r'\[\d+\s*,\s*\d+(?:\s*,\s*\d+)*\]',               # [1, 2, 3]
            r'\[[A-Z][a-z]+\s+et\s+al\.\s*,?\s*\d{4}\]',       # [Smith et al., 2020]
            r'\([A-Z][a-z]+\s+et\s+al\.\s*,?\s*\d{4}\)',       # (Smith et al., 2020)
            r'\([A-Z][a-z]+\s+and\s+[A-Z][a-z]+\s*,?\s*\d{4}\)',  # (Smith and Jones, 2020)
            r'\[[A-Z][a-z]+\s+and\s+[A-Z][a-z]+\s*,?\s*\d{4}\]',  # [Smith and Jones, 2020]
            r'\([A-Z][a-z]+\s*,?\s*\d{4}\)',                   # (Smith, 2020)
        ]
        
        for pattern in patterns:
            text = self._protect_pattern(text, pattern, ProtectionType.CITE)
        
        return text
    
    def _protect_urls(self, text: str) -> str:
        """URLを保護"""
        pattern = r'https?://[^\s<>"\)]+|www\.[^\s<>"\)]+'
        return self._protect_pattern(text, pattern, ProtectionType.URL)
    
    def _protect_terms(self, text: str) -> str:
        """専門用語を保護"""
        if not self.glossary:
            return text
        
        # 用語を長い順にソート（部分一致を防ぐ）
        sorted_terms = sorted(self.glossary.keys(), key=len, reverse=True)
        
        protected_text = text
        
        for term in sorted_terms:
            # \b は記号を含む用語（C++, k-means, .NET）でマッチしないため、
            # 用語の先頭/末尾が英数字かどうかで境界条件を切り替える。
            left_boundary  = r'(?<![A-Za-z0-9])' if term[:1].isalnum() else r''
            right_boundary = r'(?![A-Za-z0-9])'  if term[-1:].isalnum() else r''
            pattern = re.compile(
                left_boundary + re.escape(term) + right_boundary,
                re.IGNORECASE
            )

            matches = list(pattern.finditer(protected_text))
            
            for match in reversed(matches):  # 後ろから置換
                original = match.group(0)
                placeholder = self._make_placeholder(ProtectionType.TERM)
                
                # 復元時は日本語訳を使用
                item = ProtectedItem(
                    type=ProtectionType.TERM,
                    placeholder=placeholder,
                    original=original,
                    replacement=self.glossary[term]
                )
                
                self.protected_items.append(item)
                
                # 置換
                protected_text = (
                    protected_text[:match.start()] + 
                    placeholder + 
                    protected_text[match.end():]
                )
        
        return protected_text
    
    def get_stats(self) -> Dict[str, int]:
        """保護統計を取得"""
        stats = {}
        for item in self.protected_items:
            type_name = item.type.value
            stats[type_name] = stats.get(type_name, 0) + 1
        return stats
    
    def clear(self):
        """保護アイテムをクリア"""
        self.protected_items = []
        self.counters = {}


def test_protector():
    """テスト"""
    text = r"""
    We propose a novel approach with $O(n \log n)$ complexity.
    The algorithm is described in Figure 3 and Equation (5).
    See [12] for details. The loss function is:
    
    $$L = \sum_{i=1}^n (y_i - \hat{y}_i)^2$$
    
    Machine learning models achieve high accuracy.
    Visit https://example.com for code.
    """
    
    glossary = {
        "machine learning": "機械学習",
        "complexity": "計算量",
        "accuracy": "精度"
    }
    
    protector = ContentProtector(glossary)
    
    print("=" * 60)
    print("Original:")
    print(text)
    
    print("\n" + "=" * 60)
    protected = protector.protect(text)
    print("Protected:")
    print(protected)
    
    print("\n" + "=" * 60)
    print("Statistics:")
    for ptype, count in protector.get_stats().items():
        print(f"  {ptype}: {count}")
    
    print("\n" + "=" * 60)
    # 翻訳をシミュレート（プレースホルダをそのまま保持）
    simulated_translation = protected.replace(
        "We propose a novel approach with",
        "我々は新しいアプローチを提案する"
    )
    
    restored = protector.restore(simulated_translation)
    print("Restored:")
    print(restored)


if __name__ == "__main__":
    test_protector()
