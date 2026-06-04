#!/usr/bin/env python3
"""
翻訳デバッグスクリプト
翻訳エンジンが正常に動作しているか確認する
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def test_deepl():
    """DeepLのテスト"""
    api_key = os.environ.get("DEEPL_API_KEY", "")
    
    if not api_key:
        print("❌ DEEPL_API_KEY が設定されていません")
        return False
    
    print(f"🔑 DeepL APIキー: {api_key[:8]}...")
    
    try:
        import deepl
        client = deepl.Translator(api_key)
        
        # テスト翻訳
        result = client.translate_text(
            "Hello, this is a test.",
            source_lang="EN",
            target_lang="JA"
        )
        print(f"✅ DeepL 翻訳成功: {result.text}")
        
        # 使用量確認
        usage = client.get_usage()
        print(f"   使用量: {usage.character.count:,} / {usage.character.limit:,} 文字")
        return True
        
    except Exception as e:
        print(f"❌ DeepL エラー: {e}")
        return False


def test_ollama():
    """Ollamaのテスト"""
    model = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b-instruct-q5_K_M")
    
    try:
        import ollama
        
        print(f"🤖 Ollamaモデル: {model}")
        
        response = ollama.generate(
            model=model,
            prompt="Translate to Japanese: 'Hello, this is a test.'",
            options={"temperature": 0.1, "num_predict": 100}
        )
        
        print(f"✅ Ollama 翻訳成功: {response['response'].strip()}")
        return True
        
    except Exception as e:
        print(f"❌ Ollama エラー: {e}")
        return False


def test_pipeline_translation(pdf_path: str = None):
    """パイプラインの翻訳テスト（小さなテキストで）"""
    print("\n🧪 翻訳エンジン直接テスト...")
    
    try:
        from src.translation.translator import TranslationEngine
        
        translator = TranslationEngine()
        
        test_text = """
【段落1】
Large networks often exhibit a certain structure, where nodes form strongly interconnected communities.

【段落2】
The substantial progress in practical algorithms for satisfiability has opened up new possibilities.
"""
        
        print("入力テキスト:")
        print(test_text)
        print()
        
        result = translator.translate(test_text, show_stats=True)
        
        print("翻訳結果:")
        print(result)
        print()
        
        # 【段落N】が保持されているか確認
        import re
        matches = re.findall(r'【(\d+)】', result)
        print(f"段落番号の保持: {len(matches)}/2 {'✅' if len(matches) == 2 else '❌'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 翻訳エンジンエラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_structure_json(json_path: str):
    """structure.jsonの翻訳状況を確認"""
    import json
    
    json_path = Path(json_path)
    if not json_path.exists():
        print(f"❌ {json_path} が見つかりません")
        return
    
    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"\n📊 {json_path} の翻訳状況:")
    
    total = 0
    translated = 0
    untranslated_samples = []
    
    for page in data.get("pages", []):
        for block in page.get("blocks", []):
            if block.get("type") in ["paragraph", "abstract", "heading1", "heading2", "heading3", "caption", "title"]:
                total += 1
                if block.get("is_translated"):
                    translated += 1
                else:
                    if len(untranslated_samples) < 5:
                        untranslated_samples.append(block.get("content", "")[:60])
    
    print(f"   翻訳済み: {translated}/{total} ({translated/max(total,1)*100:.0f}%)")
    
    if untranslated_samples:
        print(f"\n   未翻訳サンプル:")
        for s in untranslated_samples:
            print(f"   - {s}")


def main():
    print("="*60)
    print("翻訳デバッグツール")
    print("="*60)
    print()
    
    # 1. 環境確認
    print("1️⃣  翻訳エンジンの確認")
    print("-"*40)
    
    deepl_ok = test_deepl()
    print()
    ollama_ok = test_ollama()
    print()
    
    if not deepl_ok and not ollama_ok:
        print("❌ 利用可能な翻訳エンジンがありません！")
        print()
        print("解決方法:")
        print("  A. DeepLを使う場合: .envに DEEPL_API_KEY=your_key を追加")
        print("  B. Ollamaを使う場合: ollama serve を別ターミナルで実行")
        return 1
    
    # 2. パイプラインテスト
    print("\n2️⃣  翻訳パイプラインのテスト")
    print("-"*40)
    pipeline_ok = test_pipeline_translation()
    
    # 3. JSONの確認（引数があれば）
    if len(sys.argv) > 1:
        print("\n3️⃣  翻訳状況の確認")
        print("-"*40)
        check_structure_json(sys.argv[1])
    else:
        print("\n💡 翻訳済みJSONを確認するには:")
        print("   python debug_translation.py output/論文名/structure.json")
    
    print()
    print("="*60)
    if pipeline_ok:
        print("✅ 翻訳エンジンは正常です")
        print()
        print("翻訳を実行するには:")
        print("   python main.py paper.pdf --translate --page-mode")
    else:
        print("❌ 翻訳エンジンに問題があります（上記のエラーを確認）")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
