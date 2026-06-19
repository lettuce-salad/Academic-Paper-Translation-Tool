#!/usr/bin/env python3
"""
学術論文翻訳システム v2.0
メインエントリーポイント
"""
import sys
import io
from pathlib import Path

# Windows標準コンソールの絵文字UnicodeEncodeError対策
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# パスを追加
sys.path.insert(0, str(Path(__file__).parent))

# 環境変数を読み込み
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenvがインストールされていません")
    print("   インストール: pip install python-dotenv")

from src.parser.structure_parser import PDFStructureParser
from src.renderer.layout_renderer import LayoutHTMLRenderer
from src.renderer.dual_renderer import DualColumnRenderer
from src.pipeline import TranslationPipeline


def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='学術論文翻訳システム v2.0',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # PDF翻訳（完全版）
  python main.py input.pdf --translate
  
  # 用語辞書を指定して翻訳
  python main.py input.pdf --translate --glossary config/glossary.json
  
  # 構造解析のみ（翻訳なし）
  python main.py input.pdf --parse-only
  
  # JSONから直接HTML生成
  python main.py --from-json structure.json
  
環境変数:
  DEEPL_API_KEY       DeepL APIキー
  GOOGLE_PROJECT_ID   Google Cloud プロジェクトID
  OLLAMA_MODEL        Ollamaモデル名
        """
    )
    
    parser.add_argument('input', help='入力ファイル（PDF または JSON）')
    parser.add_argument('--translate', '-t', action='store_true',
                       help='翻訳を実行（デフォルトはレイアウト表示のみ）')
    parser.add_argument('--page-mode', action='store_true',
                       help='ページ単位で翻訳（より自然な翻訳）')
    parser.add_argument('--dual-column', action='store_true',
                       help='原文・翻訳を2カラムで並列表示')
    parser.add_argument('--side-by-side', action='store_true',
                       help='左:PDF原文画像 / 右:翻訳テキスト の並列表示')
    parser.add_argument('--parse-only', action='store_true', 
                       help='構造解析のみ（JSONを出力）')
    parser.add_argument('--from-json', action='store_true',
                       help='JSONから読み込み')
    parser.add_argument('--pdf', default=None,
                       help='--from-json --side-by-side 時の元PDFパス')
    parser.add_argument('--scale', type=float, default=0.8,
                       help='HTML表示スケール（デフォルト: 0.8）')
    parser.add_argument('--output', '-o', help='出力HTMLファイル名')
    parser.add_argument('--glossary', '-g', help='用語辞書ファイル（JSON）')
    parser.add_argument('--deepl-key', help='DeepL APIキー')
    parser.add_argument('--google-project', help='Google Cloud プロジェクトID')
    parser.add_argument('--ollama-model', default='qwen2.5:7b-instruct-q5_K_M',
                       help='Ollamaモデル名')
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    if not input_path.exists():
        print(f"エラー: {input_path} が見つかりません")
        return 1
    
    print("="*60)
    print("学術論文翻訳システム v2.0")
    print("="*60)
    print()
    
    # 翻訳モード
    if args.translate and not args.from_json:
        pipeline = TranslationPipeline(
            deepl_api_key=args.deepl_key,
            google_project_id=args.google_project,
            ollama_model=args.ollama_model,
            glossary_path=args.glossary,
        )
        
        pipeline.translate_pdf(
            pdf_path=str(input_path),
            output_html=args.output,
            scale=args.scale,
            page_mode=args.page_mode
        )
        
        return 0
    
    # JSONから読み込み
    if args.from_json:
        from src.parser.pdf_document import PDFDocument

        print(f"📖 JSONを読み込み中: {input_path}")
        doc = PDFDocument.from_json(str(input_path))

        # 出力ディレクトリ
        output_dir = input_path.parent

        if args.side_by_side:
            # PDFパスの解決（--pdf優先 → 自動検索）
            if args.pdf:
                pdf_path = args.pdf
            else:
                pdf_candidates = list(output_dir.parent.glob("*.pdf")) + list(Path(".").glob("*.pdf"))
                if not pdf_candidates:
                    print("❌ PDFファイルが見つかりません。--pdf パスを指定してください")
                    return 1
                pdf_path = str(pdf_candidates[0])
                print(f"   PDFを自動検出: {pdf_path}")
            output_path = args.output or str(output_dir / "side_by_side.html")
            from src.renderer.side_by_side_renderer import SideBySideRenderer
            renderer = SideBySideRenderer(pdf_path)
            renderer.render(doc, output_path)
            print(f"✅ 完了: {output_path}")
        elif args.dual_column:
            output_path = args.output or str(output_dir / "dual.html")
            renderer = DualColumnRenderer()
            renderer.render(doc, output_path)
            print(f"✅ 2カラムHTML生成完了: {output_path}")
        else:
            output_path = args.output or str(output_dir / "translated.html")
            renderer = LayoutHTMLRenderer(scale=args.scale)
            # PDFパスを渡して図表画像切り出しを有効化
            if args.pdf:
                renderer.pdf_path = args.pdf
            elif (output_dir.parent / input_path.name.replace(".json", ".pdf")).exists():
                renderer.pdf_path = str(output_dir.parent / input_path.name.replace(".json", ".pdf"))
            renderer.render(doc, output_path)
            print(f"✅ HTML生成完了: {output_path}")

        return 0
    
    # PDFを解析（翻訳なし）
    print(f"📖 PDFを解析中: {input_path}")
    parser_obj = PDFStructureParser()
    doc = parser_obj.parse(str(input_path))
    
    stats = doc.get_statistics()
    print(f"\n📊 統計:")
    print(f"  ページ数: {stats['page_count']}")
    print(f"  総ブロック数: {stats['total_blocks']}")
    print(f"  翻訳対象ブロック: {stats['translatable_blocks']}")
    print(f"  総文字数: {stats['total_characters']:,}")
    
    print(f"\n  ブロックタイプ:")
    for block_type, count in stats['block_types'].items():
        print(f"    {block_type}: {count}")
    
    # JSONに保存
    json_path = input_path.stem + "_structure.json"
    doc.to_json(json_path)
    print(f"\n💾 構造をJSONに保存: {json_path}")
    
    if args.parse_only:
        return 0
    
    # HTML生成（翻訳なし）
    print(f"\n🎨 HTMLを生成中...")
    output_path = args.output or input_path.stem + "_layout.html"
    
    renderer = LayoutHTMLRenderer(scale=args.scale)
    renderer.render(doc, output_path)
    
    print(f"✅ 完了: {output_path}")
    print(f"\n💡 ヒント: 翻訳するには --translate オプションを追加してください")
    print(f"   python main.py {input_path} --translate")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
