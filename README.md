# 学術論文翻訳システム v2.0

英語の学術論文PDFを、レイアウト・数式・図表・専門用語を保持したまま日本語に翻訳するツール。

> **ライセンス / 利用条件**
> 本ソフトウェアは**私的利用（個人的な学習・研究目的）に限り**使用できます。
> 商用利用、再配布、公開サービスへの組み込みは認められません。
> 翻訳対象の論文の著作権は各権利者に帰属します。利用者は対象論文の利用規約・著作権法を遵守してください。
> 詳細は [LICENSE](LICENSE) を参照してください。

## 特徴

- **構造保持**: PDFの見出し・段落・図表・数式を解析して再現
- **2段組み対応**: 左段→右段の正しい読み順で翻訳
- **コンテンツ保護**: 数式・引用番号・URL・専門用語を翻訳から保護し、後で復元
- **3エンジン対応**: DeepL → Google → Ollama のフォールバック
- **用語辞書**: 225語のML/SAT分野用語を同梱（`config/glossary.json`）
- **3つの出力形式**: 通常HTML / 2カラム対照 / PDF原文対照

## インストール

```bash
pip install -r requirements.txt
```

翻訳エンジンは少なくとも1つが必要です。

- **DeepL**（推奨）: `.env` に `DEEPL_API_KEY=your_key` を記述（→ `SETUP_DEEPL.md`）
- **Ollama**（ローカル）: `ollama serve` を起動

## 使い方

```bash
# 翻訳（推奨：ブロック単位・コンテキスト付き）
python main.py paper.pdf --translate --page-mode --glossary config/glossary.json
```

出力は `output/<論文名>/` に生成されます。

```
output/paper/
├── translated.html      通常表示
├── side_by_side.html    PDF原文 ↔ 翻訳 対照表示
└── structure.json       解析結果（再生成・再開に使用）
```

### その他のコマンド

```bash
# 構造解析のみ（翻訳しない）
python main.py paper.pdf --parse-only

# JSONからHTMLを再生成
python main.py output/paper/structure.json --from-json --side-by-side --pdf paper.pdf

# 中断した翻訳を再開
python resume.py output/paper/structure.json

# 翻訳エンジンの動作確認
python debug_translation.py
```

## テスト

```bash
pytest tests/
```

`tests/` には保護機能の対称性・読み順・JSON往復の回帰テストが含まれます。

## ドキュメント

詳細な解説は `docs/` を参照してください。

- `docs/PAGE_MODE_GUIDE.md` — 翻訳モードの解説
- `docs/CONTEXT_GUIDE.md` — コンテキスト付き翻訳
- `docs/FIGURE_TABLE_GUIDE.md` — 図表検出
- `docs/LAYOUT_GUIDE.md` — レイアウト再現
- `SETUP_DEEPL.md` — DeepL設定
- `TROUBLESHOOTING.md` — トラブルシューティング

## 既知の制限

- 罫線のない・背景色のない表（空白整形のみ）は検出できない
- 図中のテキストや数式は英語のまま（図は画像として保持）
- レイアウトはフロー配置（テキスト重なり防止のため、PDF座標の厳密再現ではない）

## ライセンス

本ソフトウェアは**私的利用に限ります**（個人的な学習・研究目的）。商用利用・再配布・公開サービスへの組み込みは認められません。詳細は [LICENSE](LICENSE) を参照してください。

翻訳対象の論文の著作権は各権利者に帰属します。本ツールの利用にあたっては、対象論文の利用規約および著作権法を遵守してください。
