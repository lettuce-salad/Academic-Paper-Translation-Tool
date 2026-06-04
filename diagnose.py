#!/usr/bin/env python3
"""
診断スクリプト
システムの状態を確認
"""
import sys
import os
from pathlib import Path

print("="*60)
print("学術論文翻訳システム v2.0 - 診断")
print("="*60)
print()

# 1. Pythonバージョン
print("📌 Pythonバージョン:")
print(f"   {sys.version}")
print()

# 2. 必要なパッケージ
print("📦 必要なパッケージ:")

packages = {
    "PyMuPDF": "fitz",
    "deepl": "deepl",
    "google-cloud-translate": "google.cloud.translate_v3",
    "ollama": "ollama",
    "python-dotenv": "dotenv"
}

for display_name, import_name in packages.items():
    try:
        if "." in import_name:
            parts = import_name.split(".")
            mod = __import__(parts[0])
            for part in parts[1:]:
                mod = getattr(mod, part)
        else:
            __import__(import_name)
        print(f"   ✅ {display_name}")
    except ImportError:
        print(f"   ❌ {display_name} (未インストール)")
print()

# 3. Ollamaの状態
print("🤖 Ollama:")

try:
    import ollama
    
    # モデル一覧を取得
    try:
        models = ollama.list()
        print(f"   ✅ Ollamaサーバー: 起動中")
        print(f"   📋 利用可能なモデル:")
        
        if hasattr(models, 'models') and models.models:
            for model in models.models:
                model_name = model.model if hasattr(model, 'model') else str(model)
                print(f"      - {model_name}")
        elif isinstance(models, dict) and 'models' in models:
            for model in models['models']:
                model_name = model.get('name', model.get('model', str(model)))
                print(f"      - {model_name}")
        else:
            print(f"      (モデル情報の取得に失敗)")
            print(f"      詳細: {models}")
    
    except Exception as e:
        print(f"   ❌ Ollamaサーバー: 停止中")
        print(f"   エラー: {e}")
        print()
        print(f"   解決方法:")
        print(f"   1. 別のターミナルで 'ollama serve' を実行")
        print(f"   2. モデルをダウンロード:")
        print(f"      ollama pull qwen2.5:7b-instruct-q5_K_M")

except ImportError:
    print(f"   ❌ Ollamaパッケージがインストールされていません")
    print(f"   インストール: pip install ollama")

print()

# 4. 環境変数
print("🔑 環境変数:")

env_vars = {
    "DEEPL_API_KEY": "DeepL APIキー",
    "GOOGLE_PROJECT_ID": "Google プロジェクトID",
    "OLLAMA_MODEL": "Ollamaモデル名"
}

for var, description in env_vars.items():
    value = os.getenv(var)
    if value:
        # APIキーは一部のみ表示
        if "KEY" in var and len(value) > 10:
            display_value = value[:8] + "..." + value[-4:]
        else:
            display_value = value
        print(f"   ✅ {var}: {display_value}")
    else:
        print(f"   ⚠️  {var}: 未設定")

print()

# 5. 用語辞書
print("📖 用語辞書:")

glossary_path = Path("config/glossary.json")
if glossary_path.exists():
    import json
    with open(glossary_path, 'r', encoding='utf-8') as f:
        glossary = json.load(f)
    print(f"   ✅ config/glossary.json: {len(glossary)}語")
else:
    print(f"   ⚠️  config/glossary.json: 見つかりません")

print()

# 6. 推奨設定
print("💡 推奨設定:")
print()

# Ollamaチェック
try:
    import ollama
    try:
        ollama.list()
        print("   ✅ Ollamaは正常に動作しています")
    except:
        print("   ⚠️  Ollamaサーバーが起動していません")
        print("      → 別のターミナルで 'ollama serve' を実行してください")
except ImportError:
    print("   ❌ Ollamaがインストールされていません")
    print("      → pip install ollama")

print()

# DeepLチェック
deepl_key = os.getenv("DEEPL_API_KEY")
if deepl_key and len(deepl_key) > 10:
    print("   ✅ DeepL APIキーが設定されています（高品質翻訳が利用可能）")
else:
    print("   💡 DeepL APIキーを設定すると翻訳品質が向上します")
    print("      → https://www.deepl.com/pro-api で無料登録")
    print("      → export DEEPL_API_KEY='your-key'")

print()
print("="*60)
print("診断完了")
print("="*60)
print()

# 7. 簡易テスト
print("🧪 簡易テスト:")
print()

try:
    import ollama
    
    print("   Ollamaテスト中...")
    
    # 利用可能なモデルを取得
    try:
        models_response = ollama.list()
        
        # モデルリストを取得
        available_models = []
        if hasattr(models_response, 'models'):
            available_models = [m.model if hasattr(m, 'model') else str(m) for m in models_response.models]
        elif isinstance(models_response, dict) and 'models' in models_response:
            available_models = [m.get('name', m.get('model', str(m))) for m in models_response['models']]
        
        if not available_models:
            print(f"   ❌ モデルが見つかりません")
            print(f"   解決方法: ollama pull qwen2.5:7b-instruct-q5_K_M")
        else:
            # 最初のモデルでテスト
            test_model = available_models[0]
            print(f"   テストモデル: {test_model}")
            
            response = ollama.generate(
                model=test_model,
                prompt="Translate to Japanese: Hello",
                options={"num_ctx": 512}
            )
            
            result = response['response'].strip()
            print(f"   翻訳結果: {result}")
            print(f"   ✅ Ollama翻訳テスト成功")
    
    except Exception as e:
        print(f"   ❌ Ollamaテスト失敗: {e}")

except ImportError:
    print(f"   ⚠️  Ollamaがインストールされていないためテストをスキップ")

print()
print("="*60)
