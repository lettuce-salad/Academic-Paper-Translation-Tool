"""
Translation Pipeline
エンドツーエンドの翻訳パイプライン
"""
import time
from pathlib import Path
from typing import Optional, Callable, Dict, List
import json

from .parser.pdf_document import PDFDocument, BlockType
from .parser.structure_parser import PDFStructureParser
from .translation.translator import TranslationEngine
from .renderer.layout_renderer import LayoutHTMLRenderer


class TranslationPipeline:
    """
    翻訳パイプライン
    
    PDF → 構造解析 → 翻訳 → HTML出力
    """

    # 翻訳設定の定数
    CONTEXT_WINDOW = 2       # 前後何ブロックをコンテキストに含めるか
    API_SLEEP_SEC = 0.05    # API系エンジンのレート制限対策スリープ
    MAX_ERRORS = 10         # 連続エラーの許容上限

    def __init__(self, 
                 deepl_api_key: Optional[str] = None,
                 google_project_id: Optional[str] = None,
                 ollama_model: str = "qwen2.5:7b-instruct-q5_K_M",
                 glossary_path: Optional[str] = None,
                 progress_callback: Optional[Callable[[float, str], None]] = None):
        """
        Args:
            deepl_api_key: DeepL APIキー
            google_project_id: Google Cloud プロジェクトID
            ollama_model: Ollamaモデル名
            glossary_path: 用語辞書ファイルパス（JSON）
            progress_callback: 進捗コールバック (progress, message)
        """
        self.progress_callback = progress_callback
        
        # 用語辞書を読み込み
        glossary = {}
        if glossary_path and Path(glossary_path).exists():
            with open(glossary_path, 'r', encoding='utf-8') as f:
                glossary = json.load(f)
        
        # コンポーネント初期化
        self.parser = PDFStructureParser()
        self.translator = TranslationEngine(
            deepl_api_key=deepl_api_key,
            google_project_id=google_project_id,
            ollama_model=ollama_model,
            glossary=glossary
        )
        self.renderer = LayoutHTMLRenderer()
    
    def translate_pdf(self, 
                      pdf_path: str, 
                      output_html: Optional[str] = None,
                      output_json: Optional[str] = None,
                      scale: float = 0.8,
                      page_mode: bool = False) -> PDFDocument:
        """
        PDFを翻訳
        
        Args:
            pdf_path: 入力PDFパス
            output_html: 出力HTMLパス（Noneなら自動生成）
            output_json: 出力JSONパス（Noneなら自動生成）
            scale: HTML表示スケール
            page_mode: ページ単位翻訳モード
            
        Returns:
            翻訳済みPDFDocument
        """
        pdf_path = Path(pdf_path).resolve()
        
        # output/論文名 ディレクトリを作成（PDFと同じ階層を基準に絶対パス化）
        output_dir = (Path.cwd() / "output" / pdf_path.stem).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n📁 出力先: {output_dir}")
        
        if output_html is None:
            output_html = str(output_dir / "translated.html")
        
        if output_json is None:
            output_json = str(output_dir / "structure.json")
        
        # ステップ1: PDF構造解析
        self._report_progress(0, "PDFを解析中...")
        print(f"\n📖 PDFを解析中: {pdf_path}")
        
        doc = self.parser.parse(str(pdf_path))
        
        stats = doc.get_statistics()
        print(f"   ページ数: {stats['page_count']}")
        print(f"   総ブロック数: {stats['total_blocks']}")
        print(f"   翻訳対象: {stats['translatable_blocks']}ブロック")
        print(f"   総文字数: {stats['total_characters']:,}文字")
        
        self._report_progress(10, "解析完了")
        
        # ステップ2: 翻訳
        if page_mode:
            # ページ単位翻訳
            self._translate_by_page(doc)
        else:
            # セクション単位翻訳
            self._translate_blocks_with_context(doc)
        
        # ステップ3: JSON保存
        self._report_progress(85, "JSONに保存中...")
        doc.to_json(output_json)
        print(f"\n💾 構造をJSONに保存: {output_json}")
        
        # ステップ4: HTML生成
        self._report_progress(90, "HTMLを生成中...")
        print(f"🎨 HTMLを生成中...")
        
        self.renderer.scale = scale
        self.renderer.pdf_path = str(pdf_path)
        self.renderer.render(doc, output_html)
        print(f"   ✅ 通常表示: {output_html}")
        
        # Side-by-side（PDF画像 + 翻訳テキスト）を自動生成
        try:
            from .renderer.side_by_side_renderer import SideBySideRenderer
            sbs_path = str(output_dir / "side_by_side.html")
            sbs_renderer = SideBySideRenderer(str(pdf_path))
            sbs_renderer.render(doc, sbs_path)
            print(f"   ✅ 対照表示: {sbs_path}")
        except Exception as e:
            print(f"   ⚠️  対照表示の生成に失敗: {e}")
        
        # ステップ5: 統計表示
        self._report_progress(95, "統計を集計中...")
        usage = self.translator.get_usage()
        
        print(f"\n📊 翻訳エンジン使用量:")
        for engine, chars in usage.items():
            if chars > 0:
                print(f"   {engine}: {chars:,}文字")
        
        self._report_progress(100, "完了！")
        
        print(f"\n✨ 完了！")
        print(f"   通常表示:   {output_html}")
        print(f"   対照表示:   {output_dir / 'side_by_side.html'}")
        print(f"   JSON:       {output_json}")
        
        return doc
    
    def _translate_by_page(self, doc: PDFDocument):
        """ページ単位で翻訳"""
        self._report_progress(20, "翻訳を開始...")
        print(f"\n🔄 翻訳中（ページモード）...")
        
        from .page_mode import PageModeTranslator
        
        page_translator = PageModeTranslator(self.translator)
        page_translator.translate_document(doc)
        
        print(f"\n✅ 翻訳完了")
    
    def _translate_blocks_with_context(self, doc: PDFDocument):
        """
        ブロック単位で翻訳（同一ページ内の前後コンテキスト付き）。

        1ブロック = 1翻訳リクエスト。コンテキストはOllamaのみでDeepL/Googleでは
        translator.translate_block が自動的に生テキストのみ送信する。
        コンテキストはページをまたがず、同一ページ内のブロックに限定する。
        """
        self._report_progress(20, "翻訳を開始...")
        print(f"\n🔄 翻訳中（ブロック単位・コンテキスト付き）...")

        total_blocks = sum(len(p.get_translatable_blocks()) for p in doc.pages)
        print(f"   翻訳対象: {total_blocks}ブロック")

        translated_count = 0
        error_count = 0
        is_api = self.translator.uses_api_engine

        for page in doc.pages:
            page_blocks = page.get_translatable_blocks()

            for idx, block in enumerate(page_blocks):
                progress = 20 + (translated_count / max(total_blocks, 1)) * 60
                self._report_progress(progress, f"翻訳中: {translated_count+1}/{total_blocks}")

                if translated_count % 5 == 0 or translated_count < 3:
                    print(f"\n   [{translated_count+1}/{total_blocks}] P{page.number} {block.type.value}")

                try:
                    # 全ブロック列における現在ブロックの位置を基準に、
                    # 非翻訳ブロック（数式・図表）はプレースホルダとして
                    # コンテキストに含める（論理的なつながりを保つ）
                    ctx_before, ctx_after = self._build_context(page, block)

                    translated, engine = self.translator.translate_block(
                        block.content, ctx_before, ctx_after,
                        show_stats=(translated_count < 2)
                    )
                    translated = translated.strip()

                    if translated:
                        # 再翻訳時に初回の原文を失わないよう、未翻訳のときだけ保存
                        if not block.is_translated:
                            block.original_content = block.content
                        block.content = translated
                        block.is_translated = True
                        translated_count += 1
                    else:
                        print(f"      ⚠️  空の翻訳結果")
                        block.is_translated = False

                    # レート制限対策はAPI系のみ（Ollamaはローカルなので不要）
                    if is_api:
                        time.sleep(self.API_SLEEP_SEC)

                except KeyboardInterrupt:
                    print(f"\n\n⚠️  中断: {translated_count}/{total_blocks}ブロック翻訳済み")
                    raise
                except Exception as e:
                    error_count += 1
                    print(f"\n   ⚠️  ブロック翻訳失敗: {e}")
                    if error_count > self.MAX_ERRORS:
                        raise Exception(f"翻訳エラーが多発しています ({error_count}件)")
                    block.is_translated = False
                    continue

        print(f"\n✅ 翻訳完了")
        print(f"   成功: {translated_count}/{total_blocks}ブロック")
        if error_count > 0:
            print(f"   エラー: {error_count}ブロック")

    # 非翻訳ブロックのコンテキスト用プレースホルダ
    _CONTEXT_PLACEHOLDER = {
        BlockType.EQUATION: "[数式]",
        BlockType.FIGURE: "[図]",
        BlockType.TABLE: "[表]",
        BlockType.CAPTION: "[キャプション]",
    }

    def _build_context(self, page, target_block):
        """
        target_block の前後コンテキストを、同一ページの全ブロック列から構築する。

        翻訳対象ブロックは原文を、数式・図表などの非翻訳ブロックは
        プレースホルダ（[数式] など）を入れることで、論理的な文脈の
        途切れを防ぐ。
        """
        all_blocks = page.blocks
        try:
            pos = all_blocks.index(target_block)
        except ValueError:
            return [], []

        def repr_block(b):
            if b.metadata.get("inside_table") or b.metadata.get("inside_figure"):
                return None  # 図表内テキストはコンテキストに含めない
            if b.type in (BlockType.HEADER, BlockType.FOOTER):
                return None
            return self._CONTEXT_PLACEHOLDER.get(b.type, b.content)

        ctx_before = []
        for b in all_blocks[max(0, pos - self.CONTEXT_WINDOW):pos]:
            r = repr_block(b)
            if r:
                ctx_before.append(r)

        ctx_after = []
        for b in all_blocks[pos + 1:pos + 1 + self.CONTEXT_WINDOW]:
            r = repr_block(b)
            if r:
                ctx_after.append(r)

        return ctx_before, ctx_after

    def _report_progress(self, progress: float, message: str):
        """進捗を報告"""
        if self.progress_callback:
            self.progress_callback(progress, message)
