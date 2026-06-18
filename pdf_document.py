"""
Page Mode Translation
ページ単位でブロックを翻訳（同一ページ内コンテキスト付き）
"""
from typing import List
from .parser.pdf_document import PDFDocument, BlockType


class PageModeTranslator:
    """
    ページ単位でブロックを翻訳。
    1ブロック1翻訳でズレを排除し、同一ページ内の前後コンテキストで文脈を保持する。
    コンテキスト付与は translator.translate_block がエンジンに応じて自動制御する
    （DeepL/Googleは生テキスト、Ollamaはコンテキスト付きプロンプト）。
    """

    CONTEXT_WINDOW = 2
    MAX_ERRORS = 10

    def __init__(self, translator):
        self.translator = translator

    def translate_document(self, doc: PDFDocument) -> None:
        """ドキュメントを翻訳（in-place、戻り値なし）。"""
        total_pages = len(doc.pages)
        error_count = 0

        for page_idx, page in enumerate(doc.pages):
            print(f"\n📄 ページ {page_idx + 1}/{total_pages} を翻訳中...")

            translatable_blocks = [
                b for b in page.blocks
                if b.type in [
                    BlockType.TITLE, BlockType.ABSTRACT,
                    BlockType.HEADING1, BlockType.HEADING2, BlockType.HEADING3,
                    BlockType.PARAGRAPH, BlockType.CAPTION, BlockType.LIST_ITEM
                ]
            ]

            if not translatable_blocks:
                continue

            translated_count = 0

            for idx, block in enumerate(translatable_blocks):
                ctx_before = [b.content for b in translatable_blocks[max(0, idx - self.CONTEXT_WINDOW):idx]]
                ctx_after  = [b.content for b in translatable_blocks[idx + 1:idx + 1 + self.CONTEXT_WINDOW]]

                try:
                    result, engine = self.translator.translate_block(
                        block.content, ctx_before, ctx_after,
                        show_stats=(idx == 0)
                    )
                    result = result.strip()
                    if result:
                        # 再翻訳時に初回原文を失わないよう未翻訳時のみ保存
                        if not block.is_translated:
                            block.original_content = block.content
                        block.content = result
                        block.is_translated = True
                        translated_count += 1
                except KeyboardInterrupt:
                    print(f"\n⚠️  中断されました")
                    raise
                except Exception as e:
                    error_count += 1
                    print(f"      ⚠️  ブロック {idx+1} 翻訳失敗: {e}")
                    block.is_translated = False
                    if error_count > self.MAX_ERRORS:
                        raise Exception(f"翻訳エラーが多発しています ({error_count}件)")

            print(f"   ✅ {translated_count}/{len(translatable_blocks)}ブロック翻訳完了")
