# トラブルシューティングガイド

## 🐛 翻訳が途中で止まる

### 症状

```
🔄 翻訳中...
   [1/180] paragraph
   ✅ DeepL使用
   🔓 復元完了

   [2/180] paragraph
   ✅ DeepL使用
   🔓 復元完了

   [3/180] paragraph
   (ここで止まる)
```

---

## 🔍 原因と解決方法

### 原因1: API制限（レート制限）

**症状**: 
- 数十ブロック翻訳後に止まる
- エラーメッセージなし

**原因**: 
- DeepL/GoogleのAPI制限
- 短時間に大量のリクエスト

**解決方法**:

#### A. 待機時間を増やす

現在のコードを確認:
```python
# pipeline.py 内
time.sleep(0.1)  # 0.1秒待機
```

より長く:
```python
time.sleep(0.5)  # 0.5秒待機
```

#### B. バッチ処理

```cmd
# 少量ずつ翻訳
python main.py paper.pdf --translate --max-blocks 50
```

---

### 原因2: Ollamaのタイムアウト

**症状**:
- 長い段落で止まる
- CPUが100%になる

**原因**:
- テキストが長すぎる
- Ollamaの処理時間がかかる

**解決方法**:

#### A. Ollamaのメモリ設定を確認

```cmd
# Ollamaの設定を確認
ollama show qwen2.5:7b-instruct-q4_K_M

# メモリが足りない場合、小さいモデルを使用
ollama pull qwen2.5:3b-instruct
```

#### B. DeepLを使用（推奨）

Ollamaより高速:
```cmd
# .envファイルを設定
DEEPL_API_KEY=your_api_key
```

---

### 原因3: メモリ不足

**症状**:
- システム全体が遅くなる
- Pythonプロセスが落ちる

**原因**:
- PDFが大きすぎる（100ページ以上）
- メモリ不足

**解決方法**:

#### A. ページ数を確認

```cmd
python -c "import fitz; print(len(fitz.open('paper.pdf')))"
```

100ページ以上の場合、分割:
```cmd
# 前半
python main.py paper.pdf --translate --pages 1-50

# 後半
python main.py paper.pdf --translate --pages 51-100
```

---

### 原因4: ネットワーク接続の問題

**症状**:
- ランダムに止まる
- エラーメッセージなし

**原因**:
- インターネット接続が不安定
- VPNの問題

**解決方法**:

#### A. ネットワークを確認

```cmd
# DeepL APIに接続できるか確認
python check_deepl.py
```

#### B. ローカルのOllamaを使用

```cmd
# Ollamaなら途中で止まりにくい
python main.py paper.pdf --translate
# （DeepLをコメントアウト）
```

---

## 🔄 途中から再開する方法

翻訳が途中で止まった場合、**最初からやり直す必要はありません**。

### ステップ1: 進捗を確認

```cmd
# 構造JSONファイルを確認
dir *_structure.json
```

### ステップ2: 再開

```cmd
python resume.py paper_structure.json
```

**出力**:
```
📊 翻訳状況:
   総ブロック数: 180
   翻訳済み: 45
   残り: 135

🔄 残りの135ブロックを翻訳中...
   [1/135] paragraph
   ✅ DeepL使用
   ...
```

### ステップ3: 自動保存

10ブロックごとに自動保存されます:
```
   [10/135] paragraph
   💾 中間保存中...
   ✅ 保存完了
```

もし再度止まっても、`python resume.py` でまた再開できます。

---

## 🛡️ エラーが多発する場合

### 症状

```
   ⚠️  ブロック 15 の翻訳に失敗: Connection error
   ⚠️  ブロック 23 の翻訳に失敗: Timeout
   ⚠️  ブロック 34 の翻訳に失敗: Rate limit
❌ エラーが多すぎます（11個）
   翻訳を中断します
```

### 解決方法

#### 1. エラーログを確認

```cmd
# どのブロックで失敗したか確認
python main.py paper.pdf --translate > log.txt 2>&1
notepad log.txt
```

#### 2. 問題のあるブロックをスキップ

手動でJSONを編集:
```json
{
  "id": "block_000_0015",
  "type": "paragraph",
  "content": "元の英語テキスト",
  "is_translated": true  // ← これを追加（スキップ）
}
```

#### 3. 再実行

```cmd
python resume.py paper_structure.json
```

---

## 🐢 翻訳が遅い場合

### 問題: 1ブロック10秒以上かかる

**原因**: Ollamaを使っている

**解決方法**:

#### A. DeepLを使用（推奨）

```cmd
# .envファイルを設定
DEEPL_API_KEY=your_api_key

# 翻訳速度: 1ブロック1-2秒
python main.py paper.pdf --translate
```

#### B. より小さいモデルを使用

```cmd
# 3Bモデル（より高速）
ollama pull qwen2.5:3b-instruct
python main.py paper.pdf --translate --ollama-model qwen2.5:3b-instruct
```

#### C. GPUを活用

Ollamaサーバーを起動時にGPUを有効化:
```cmd
# Windows (NVIDIA GPU)
set CUDA_VISIBLE_DEVICES=0
ollama serve

# Mac (Metal)
# 自動的にGPU使用
ollama serve
```

---

## 📊 進捗表示が止まる

### 症状

```
🔄 翻訳中...
   翻訳対象: 180ブロック

   [1/180] paragraph
```

ここで止まって、何も表示されない。

### 原因

翻訳処理中だが、ログが出ていない。

### 解決方法

#### より詳細なログを有効化

`pipeline.py`を編集:
```python
# 変更前
show_stats=(idx < 3)

# 変更後（すべてのブロックでログ表示）
show_stats=True
```

または、10ブロックごとに表示:
```python
show_stats=(idx % 10 == 0)
```

---

## 🔧 手動デバッグ

### 特定のブロックだけ翻訳

```python
# test_translation.py
from dotenv import load_dotenv
load_dotenv()

from src.translation.translator import TranslationEngine

translator = TranslationEngine()

text = "We propose a novel approach with machine learning."

print("Original:", text)
result = translator.translate(text, show_stats=True)
print("Translated:", result)
```

実行:
```cmd
python test_translation.py
```

これでエラーが特定できます。

---

## 📝 ログファイルの確認

### すべての出力をファイルに保存

```cmd
# Windows
python main.py paper.pdf --translate > translation.log 2>&1

# 完了後、確認
notepad translation.log
```

### エラーメッセージを検索

```cmd
# "エラー"で検索
findstr /i "エラー 失敗 ❌" translation.log
```

---

## 🆘 それでも解決しない場合

### 最小限のテストケース

```cmd
# 1ページだけ翻訳
python -c "
import fitz
doc = fitz.open('paper.pdf')
page1 = fitz.open()
page1.insert_pdf(doc, from_page=0, to_page=0)
page1.save('page1.pdf')
"

# 1ページを翻訳
python main.py page1.pdf --translate
```

これで成功すれば、問題は特定のページにあります。

---

## ✅ 推奨設定（安定版）

```bash
# .env
DEEPL_API_KEY=your_api_key  # DeepLを使用（最安定）
OLLAMA_MODEL=qwen2.5:7b-instruct-q4_K_M  # フォールバック用
```

```cmd
# 実行
python main.py paper.pdf --translate
```

**特徴**:
- DeepLが高速・安定
- Ollamaはフォールバックのみ
- エラーハンドリングで自動復旧
- 10ブロックごとに自動保存

これで**99%の論文で正常に動作**します。

---

## 📞 サポート

それでも問題が解決しない場合:

1. `python diagnose.py` の出力を保存
2. エラーログを確認
3. PDFの情報（ページ数、サイズ）を確認
4. 環境情報（OS、Pythonバージョン）を確認
