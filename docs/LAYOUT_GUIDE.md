# レイアウト改善ガイド

## 🎯 問題と解決方法

### 問題1: 文字が重なる

**原因**: 絶対座標配置で日本語が英語より長くなる

**解決済み** ✅
- 相対配置（フロー配置）に変更
- 自動的にスペース調整

---

### 問題2: 図表と重なる

**原因**: 図表の位置が固定で、テキストと重なる

**解決済み** ✅
- 図表をフロー配置
- テキストと図表の間に適切なマージン

---

## 📊 3つの表示モード

### モード1: 通常表示（推奨）

```cmd
python main.py paper_translated.json --from-json
```

**特徴**:
- ✅ 重なりなし
- ✅ 読みやすい
- ✅ 図表も適切に配置

**レイアウト**:
```
タイトル

Abstract
背景説明...

1. Introduction
本文...

[Figure 1: プレースホルダ]
図1: キャプション

本文続き...
```

---

### モード2: 2カラム表示（比較用）

```cmd
python main.py paper_translated.json --from-json --dual-column
```

**特徴**:
- ✅ 原文・翻訳を並列表示
- ✅ 対照しやすい
- ✅ 学習に最適

**レイアウト**:
```
┌─────────────────────┬─────────────────────┐
│ Original            │ Translation         │
├─────────────────────┼─────────────────────┤
│ Title               │ タイトル            │
│                     │                     │
│ Abstract...         │ 要旨...             │
│                     │                     │
│ Introduction...     │ はじめに...         │
└─────────────────────┴─────────────────────┘
```

---

### モード3: 画像抽出（オプション）

PDFから図を実際に抽出:

```cmd
python src/parser/figure_extractor.py paper.pdf output_folder
```

**出力**:
```
output_folder/
  ├── page001_img000.png
  ├── page001_img001.png
  ├── page003_img000.png
  └── ...
```

これらの画像を手動でHTMLに埋め込むことも可能。

---

## 🔧 カスタマイズ

### スペースを調整

`src/renderer/layout_renderer.py` を編集:

```python
# 段落間のスペース
.block.paragraph {
    margin-bottom: 12px;  # ← ここを変更（例: 20px）
}

# 図のスペース
.figure-container {
    margin: 20px 0;  # ← ここを変更（例: 30px 0）
}
```

---

### フォントサイズを変更

```python
# 本文
.block.paragraph {
    font-size: 1em;  # ← ここを変更（例: 1.1em）
}

# タイトル
.block.title {
    font-size: 1.5em;  # ← ここを変更（例: 2em）
}
```

---

## 📱 レスポンシブ対応

### PC表示

```
通常: 幅800px、読みやすい1カラム
2カラム: 幅1400px、左右に分割
```

### タブレット

```
通常: 幅100%、余白あり
2カラム: 幅100%、左右に分割
```

### スマホ

```
通常: 幅100%、余白縮小
2カラム: 上下に配置（原文→翻訳）
```

すべての画面サイズで**重なりなし** ✅

---

## 🎨 デザインのカスタマイズ

### 配色を変更

```css
/* ヘッダーの色 */
.block.heading1 {
    border-bottom: 2px solid #3498db;  /* 青 → 好きな色に */
}

/* Abstractの背景 */
.block.abstract {
    background: #f8f9fa;  /* 薄灰 → 好きな色に */
    border-left: 4px solid #3498db;
}
```

---

### 行間を調整

```css
.block.paragraph {
    line-height: 1.8;  /* ← ここを変更（例: 2.0で広く）
}
```

---

## 🖼️ 図表の扱い

### 現在の表示

**図**: プレースホルダ + キャプション
```
┌─────────────────┐
│                 │
│   Figure 1      │  ← プレースホルダ
│                 │
└─────────────────┘
図1: 性能比較
```

**表**: HTMLテーブル + キャプション
```
┌────┬────┬────┐
│ A  │ B  │ C  │
├────┼────┼────┤
│ 1  │ 2  │ 3  │
└────┴────┴────┘
表1: 実験結果
```

---

### 実際の画像を埋め込む

#### ステップ1: 画像を抽出

```cmd
python src/parser/figure_extractor.py paper.pdf images
```

#### ステップ2: HTMLに手動で埋め込み

生成されたHTMLを編集:

```html
<!-- 変更前 -->
<div class="figure-placeholder">
    <svg>Figure 1</svg>
</div>

<!-- 変更後 -->
<div class="figure-placeholder">
    <img src="images/page003_img000.png" alt="Figure 1">
</div>
```

または、Base64で直接埋め込み:

```html
<img src="data:image/png;base64,iVBORw0KG..." alt="Figure 1">
```

---

## ✅ 確認チェックリスト

HTMLを開いて確認:

- [ ] 段落が重なっていない
- [ ] 見出しと本文の間にスペースがある
- [ ] 図表と本文が重なっていない
- [ ] 図のキャプションが表示されている
- [ ] 表が正しく表示されている
- [ ] 数式がMathJaxで表示されている
- [ ] スマホでも読みやすい（レスポンシブ）
- [ ] 印刷時も適切なレイアウト

すべて ✅ なら完璧です！

---

## 🚀 高度なカスタマイズ

### CSSを完全に置き換え

独自のCSSファイルを作成:

```css
/* custom.css */
.block.paragraph {
    /* あなたのスタイル */
}
```

HTMLの `<head>` に追加:

```html
<link rel="stylesheet" href="custom.css">
```

---

### JavaScriptで拡張

スクロール同期、ハイライトなど:

```html
<script>
// 段落をクリックすると原文とリンク
document.querySelectorAll('.block').forEach(block => {
    block.addEventListener('click', () => {
        // カスタム処理
    });
});
</script>
```

---

## 💡 Tips

### 印刷時の最適化

```css
@media print {
    .block.paragraph {
        page-break-inside: avoid;  /* 段落を分割しない */
    }
    
    .figure-container {
        page-break-inside: avoid;  /* 図を分割しない */
    }
}
```

### PDFとして保存

ブラウザで開いて:
```
Ctrl + P → PDFとして保存
```

レイアウトがそのまま保持されます。

---

## 📊 ビフォー・アフター

### Before（v1.0）

```
問題1: 文字が重なる
タイトル
Abstract長い文章が次と重なるAbstract長い文章が次と重なる
1. Introduction本文が重なる

問題2: 図が変な位置
[Figure 1]本文と重なる本文と重なる
```

### After（v2.0）

```
解決1: 重ならない
タイトル

Abstract
長い文章でも自動調整

1. Introduction
本文がきれいに配置

解決2: 図が適切な位置
[Figure 1]
図1: キャプション

本文続き
```

---

これで**完璧なレイアウト**が実現できます 🎉
