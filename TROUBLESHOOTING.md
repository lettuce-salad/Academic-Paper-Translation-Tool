# DeepLセットアップガイド

## 🎯 目標

DeepL APIを使って高品質な翻訳を行う

---

## 📋 手順

### ステップ1: DeepL APIキーの取得

1. **DeepL Proにアクセス**
   - https://www.deepl.com/pro-api にアクセス

2. **無料アカウント登録**
   - 「無料で試す」をクリック
   - メールアドレスとパスワードを入力
   - メール認証を完了

3. **APIキーを取得**
   - ダッシュボードにログイン
   - 「アカウント」→「APIキー」
   - APIキーをコピー（例: `abc123de-f456-789g-h012-ijk345lmn678:fx`）

**無料枠**:
- 月間50万文字まで無料
- クレジットカード登録不要

---

### ステップ2: .envファイルを作成

#### Windows

```cmd
# paper-translator-v2フォルダに移動
cd paper-translator-v2

# .envファイルを作成
copy .env.example .env

# メモ帳で開く
notepad .env
```

#### Mac/Linux

```bash
# paper-translator-v2フォルダに移動
cd paper-translator-v2

# .envファイルを作成
cp .env.example .env

# エディタで開く
nano .env
# または
code .env
```

---

### ステップ3: APIキーを設定

.envファイルを開いて、以下の行を編集:

**編集前**:
```
DEEPL_API_KEY=your_deepl_api_key_here
```

**編集後**:
```
DEEPL_API_KEY=abc123de-f456-789g-h012-ijk345lmn678:fx
```

↑ あなたのAPIキーに置き換える

**重要**:
- APIキーは `your_deepl_api_key_here` の部分を完全に置き換える
- スペースや改行を入れない
- ダブルクォートで囲まない

---

### ステップ4: 保存

- **Windows**: `Ctrl+S` → `Alt+F4`
- **Mac**: `Cmd+S` → `Cmd+Q`
- **Linux**: `Ctrl+O` → `Enter` → `Ctrl+X`

---

### ステップ5: 確認

```cmd
# DeepL診断を実行
python check_deepl.py
```

**期待される出力**:
```
====================================================
DeepL診断
====================================================

📦 ステップ1: python-dotenvの確認
   ✅ python-dotenvインストール済み
   ✅ .envファイルを読み込みました

📦 ステップ2: deeplパッケージの確認
   ✅ deeplパッケージインストール済み

🔑 ステップ3: 環境変数の確認
   ✅ DEEPL_API_KEY: abc123de...n678

🧪 ステップ4: DeepL接続テスト
   ✅ DeepL Translatorオブジェクト作成成功
   テスト翻訳: 'Hello, world!' → 日本語
   結果: こんにちは、世界！
   ✅ DeepL翻訳テスト成功

====================================================
✅ DeepLは正常に動作しています！
====================================================
```

---

### ステップ6: 翻訳実行

```cmd
python main.py paper.pdf --translate
```

**期待される出力**:
```
📖 PDFを解析中: paper.pdf
   ページ数: 10
   総ブロック数: 245
   翻訳対象: 180ブロック

🔄 翻訳中...
   🔒 保護: 5個 (MATH:2, REF:2, TERM:1)
   ✅ DeepL使用               ← これが表示されればOK！
   🔓 復元完了 (使用エンジン: DeepL)
```

---

## 🐛 トラブルシューティング

### エラー1: `DEEPL_API_KEY: 未設定`

**原因**: .envファイルが作成されていない、または読み込まれていない

**解決方法**:
```cmd
# .envファイルを確認
dir .env

# なければ作成
copy .env.example .env
notepad .env
```

---

### エラー2: `DeepLエラー: 401 Unauthorized`

**原因**: APIキーが無効

**解決方法**:
1. APIキーが正しいか確認
2. DeepLダッシュボードで新しいAPIキーを生成
3. .envファイルを更新

---

### エラー3: `DeepLエラー: 456 Quota exceeded`

**原因**: 月間50万文字の無料枠を使い切った

**解決方法**:
- 翌月まで待つ
- または有料プランにアップグレード
- または一時的にOllamaを使用:
  ```cmd
  # .envファイルでDeepLをコメントアウト
  # DEEPL_API_KEY=abc123...
  ```

---

### エラー4: `python-dotenvがインストールされていません`

**原因**: python-dotenvパッケージがない

**解決方法**:
```cmd
pip install python-dotenv
```

---

### エラー5: `deeplパッケージがインストールされていません`

**原因**: deeplパッケージがない

**解決方法**:
```cmd
pip install deepl
```

---

## 📊 .envファイルの完全な例

```bash
# DeepL API設定
DEEPL_API_KEY=abc123de-f456-789g-h012-ijk345lmn678:fx

# Google Cloud Translation API設定（オプション）
# GOOGLE_PROJECT_ID=your_google_project_id_here
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# Ollama設定（フォールバック用）
OLLAMA_MODEL=qwen2.5:7b-instruct-q4_K_M
OLLAMA_HOST=http://localhost:11434
```

---

## 💡 Tips

### APIキーの確認

```cmd
# 環境変数が正しく設定されているか確認
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('DEEPL_API_KEY'))"
```

### 翻訳エンジンの優先順位

```
1. DeepL      ← .envで設定
2. Google     ← .envで設定（オプション）
3. Ollama     ← ローカル（フォールバック）
```

DeepLが設定されていれば、常にDeepLが使われます。

---

## ✅ チェックリスト

- [ ] DeepL APIキーを取得した
- [ ] .envファイルを作成した
- [ ] APIキーを.envに設定した
- [ ] python-dotenvをインストールした
- [ ] deeplをインストールした
- [ ] `python check_deepl.py` が成功した
- [ ] 翻訳時に「✅ DeepL使用」と表示される

すべてチェックできたら、高品質な翻訳が利用できます！🎉
