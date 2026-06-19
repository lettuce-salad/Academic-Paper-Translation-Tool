# Paper Translator v2.0 実装状況

## ✅ 実装済み機能（全て動作確認済み）

### 1. PDF構造解析
- ✅ PyMuPDFによるページ・ブロック抽出
- ✅ ブロックタイプ分類（title/abstract/heading/paragraph/equation/caption/reference）
- ✅ 座標情報保持（PyMuPDF左上原点）
- ⚠️ 表の構造解析は限定的（表全体が1ブロックになる場合あり）
- ⚠️ 段組レイアウトの完全な検出は未対応

### 2. 翻訳エンジン
- ✅ DeepL API（推奨）
- ✅ Google Translate API（フォールバック）
- ✅ Ollama ローカルLLM（フォールバック）
- ✅ 全エンジン失敗時は RuntimeError で明示

### 3. コンテンツ保護
- ✅ 数式・引用番号・URL・専門用語を翻訳から保護
- ✅ 翻訳後に自動復元

### 4. 翻訳パイプライン
- ✅ セクション単位翻訳（文脈保持）
- ✅ ページ単位翻訳 `--page-mode`
- ✅ 進捗表示・中断・再開

### 5. HTML レンダリング
- ✅ 通常表示（フロー配置）
- ✅ 2カラム表示 `--dual-column`
- ✅ PDF原文対照表示 `--side-by-side`

### 6. 図表処理
- ✅ PDFから図表を画像として切り抜きHTMLに埋め込み
- ✅ キャプション翻訳

## 主なコマンド

```cmd
# 翻訳実行（推奨）
python main.py paper.pdf --translate --page-mode

# 対照表示のみ再生成
python main.py output/paper/structure.json --from-json --side-by-side --pdf paper.pdf

# 中断後の再開
python resume.py output/paper/structure.json
```
