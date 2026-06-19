#!/usr/bin/env python3
"""
翻訳再開機能
途中で止まった翻訳を再開する
"""
import sys
import io
import json
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
    pass

from src.parser.pdf_document import PDFDocument
from src.translation.translator import TranslationEngine
from src.renderer.layout_renderer import LayoutHTMLRenderer

CONTEXT_WINDOW = 2
SAVE_INTERVAL = 10
MAX_ERRORS = 10


def resume_translation(json_path: str, output_html: str = None):
    """途中で止まった翻訳を再開"""
    json_path = Path(json_path)

    if not json_path.exists():
        print(f"❌ エラー: {json_path} が見つかりません")
        return 1

    output_dir = json_path.parent
    if output_html is None:
        output_html = str(output_dir / "translated.html")

    print("="*60)
    print("翻訳再開")
    print("="*60)
    print()

    print(f"📖 JSONを読み込み中: {json_path}")
    doc = PDFDocument.from_json(str(json_path))

    translatable_blocks = doc.get_translatable_blocks()
    already_translated = [b for b in translatable_blocks if b.is_translated]
    remaining = [b for b in translatable_blocks if not b.is_translated]

    print(f"\n📊 翻訳状況:")
    print(f"   総ブロック数: {len(translatable_blocks)}")
    print(f"   翻訳済み: {len(already_translated)}")
    print(f"   残り: {len(remaining)}")

    if len(remaining) == 0:
        print(f"\n✅ すべて翻訳済みです")
        renderer = LayoutHTMLRenderer()
        renderer.render(doc, output_html)
        print(f"✅ 完了: {output_html}")
        return 0

    print(f"\n🔄 残りの{len(remaining)}ブロックを翻訳中...")
    translator = TranslationEngine()

    # ページごとにコンテキストを組むため、ページ単位で処理
    translated_count = 0
    error_count = 0
    remaining_set = set(id(b) for b in remaining)

    for page in doc.pages:
        page_blocks = page.get_translatable_blocks()

        for idx, block in enumerate(page_blocks):
            if id(block) not in remaining_set:
                continue   # すでに翻訳済み

            print(f"\n   [{translated_count+1}/{len(remaining)}] P{page.number} {block.type.value}")

            try:
                if not block.original_content:
                    block.original_content = block.content

                # 同一ページ内コンテキスト（pipelineと同一ロジック）
                ctx_before = [b.content for b in page_blocks[max(0, idx - CONTEXT_WINDOW):idx]]
                ctx_after  = [b.content for b in page_blocks[idx + 1:idx + 1 + CONTEXT_WINDOW]]

                translated, engine = translator.translate_block(
                    block.content, ctx_before, ctx_after,
                    show_stats=(translated_count < 3)
                )
                block.content = translated.strip()
                block.is_translated = True
                translated_count += 1

                if translated_count % SAVE_INTERVAL == 0:
                    print(f"\n   💾 中間保存中...")
                    doc.to_json(str(json_path))
                    print(f"   ✅ 保存完了")

            except KeyboardInterrupt:
                print(f"\n\n⚠️  中断されました ({translated_count}/{len(remaining)})")
                doc.to_json(str(json_path))
                print(f"   💾 進捗を保存しました。再開: python resume.py {json_path}")
                return 1

            except Exception as e:
                error_count += 1
                print(f"   ⚠️  エラー: {e}")
                if error_count > MAX_ERRORS:
                    print(f"\n❌ エラーが多すぎます")
                    doc.to_json(str(json_path))
                    return 1
                continue

    print(f"\n💾 最終保存中...")
    doc.to_json(str(json_path))
    print(f"✅ 保存完了")

    print(f"\n🎨 HTMLを生成中...")
    renderer = LayoutHTMLRenderer()
    renderer.render(doc, output_html)

    print(f"\n✅ 完了: {output_html}")
    print(f"   成功: {translated_count}ブロック")
    if error_count > 0:
        print(f"   エラー: {error_count}ブロック")

    return 0


def main():
    """CLIエントリーポイント"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='途中で止まった翻訳を再開',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 途中で止まった翻訳を再開
  python resume.py paper_structure.json
  
  # 出力ファイル名を指定
  python resume.py paper_structure.json -o output.html
        """
    )
    
    parser.add_argument('json', help='構造JSONファイル')
    parser.add_argument('--output', '-o', help='出力HTMLファイル')
    
    args = parser.parse_args()
    
    return resume_translation(args.json, args.output)


if __name__ == "__main__":
    sys.exit(main())
