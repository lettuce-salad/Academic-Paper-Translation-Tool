#!/usr/bin/env python3
"""
DeepL診断スクリプト
DeepLが使われない原因を特定
"""
import os
import sys

print("="*60)
print("DeepL診断")
print("="*60)
print()

# 1. python-dotenvの確認
print("📦 ステップ1: python-dotenvの確認")
try:
    from dotenv import load_dotenv
    print("   ✅ python-dotenvインストール済み")
    load_dotenv()
    print("   ✅ .envファイルを読み込みました")
except ImportError:
    print("   ❌ python-dotenvがインストールされていません")
    print("   解決方法: pip install python-dotenv")
    sys.exit(1)
except Exception as e:
    print(f"   ⚠️  .env読み込みエラー: {e}")

print()

# 2. deeplパッケージの確認
print("📦 ステップ2: deeplパッケージの確認")
try:
    import deepl
    print("   ✅ deeplパッケージインストール済み")
except ImportError:
    print("   ❌ deeplパッケージがインストールされていません")
    print("   解決方法: pip install deepl")
    sys.exit(1)

print()

# 3. 環境変数の確認
print("🔑 ステップ3: 環境変数の確認")
api_key = os.getenv("DEEPL_API_KEY")

if api_key:
    print(f"   ✅ DEEPL_API_KEY: {api_key[:8]}...{api_key[-4:]}")
else:
    print("   ❌ DEEPL_API_KEY: 未設定")
    print()
    print("   解決方法:")
    print("   1. .envファイルを作成:")
    print("      copy .env.example .env")
    print()
    print("   2. .envファイルを編集:")
    print("      notepad .env")
    print()
    print("   3. 以下の行を編集:")
    print("      DEEPL_API_KEY=your_deepl_api_key_here")
    print("      ↓")
    print("      DEEPL_API_KEY=あなたのAPIキー")
    print()
    print("   4. APIキーの取得:")
    print("      https://www.deepl.com/pro-api")
    sys.exit(1)

print()

# 4. DeepL接続テスト
print("🧪 ステップ4: DeepL接続テスト")
try:
    translator = deepl.Translator(api_key)
    print("   ✅ DeepL Translatorオブジェクト作成成功")
    
    # 簡単な翻訳テスト
    print("   テスト翻訳: 'Hello, world!' → 日本語")
    result = translator.translate_text("Hello, world!", source_lang="EN", target_lang="JA")
    print(f"   結果: {result.text}")
    print("   ✅ DeepL翻訳テスト成功")
    
except deepl.DeepLException as e:
    print(f"   ❌ DeepLエラー: {e}")
    print()
    print("   考えられる原因:")
    print("   - APIキーが無効")
    print("   - APIキーの形式が間違っている")
    print("   - 無料枠を使い切った")
    print("   - ネットワーク接続の問題")
    sys.exit(1)
    
except Exception as e:
    print(f"   ❌ 予期しないエラー: {e}")
    sys.exit(1)

print()
print("="*60)
print("✅ DeepLは正常に動作しています！")
print("="*60)
print()
print("翻訳を実行してください:")
print("  python main.py paper.pdf --translate")
