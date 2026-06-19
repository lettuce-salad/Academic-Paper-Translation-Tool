# 文脈保持翻訳ガイド

## 🎯 問題と解決

### 問題: 文脈が失われた翻訳

**v1方式（ブロック単位）**:
```
[ブロック1] We propose a novel approach.
→ 我々は新しいアプローチを提案する。

[ブロック2] This method improves accuracy.
→ この方法は精度を向上させる。（❌ 何の方法？）

[ブロック3] It achieves 95% performance.
→ それは95%の性能を達成する。（❌ 何が？）
```

**問題点**:
- ❌ 代名詞の参照先が不明
- ❌ 段落間のつながりが不自然
- ❌ 文脈が途切れる

---

### 解決: セクション単位翻訳（v2方式）

**v2方式（セクション単位）**:
```
[セクション全体]
We propose a novel approach.
This method improves accuracy.
It achieves 95% performance.

→ 翻訳（文脈を保持）

我々は新しいアプローチを提案する。
この手法は精度を向上させる。
これにより95%の性能を達成する。
```

**改善点**:
- ✅ 代名詞が自然
- ✅ 段落間のつながりが滑らか
- ✅ 文脈が保持される

---

## 🔧 仕組み

### 1. セクション単位にグループ化

```python
# 見出しで区切る
Section 1: Title + Abstract
Section 2: 1. Introduction (全段落)
Section 3: 2. Method (全段落)
Section 4: 3. Experiments (全段落)
...
```

### 2. セクション全体を翻訳

```
元のテキスト:
[BLOCK_0000_START] Title text [BLOCK_0000_END]
[BLOCK_0001_START] Paragraph 1 [BLOCK_0001_END]
[BLOCK_0002_START] Paragraph 2 [BLOCK_0002_END]

↓ 翻訳（文脈保持）

翻訳後:
[BLOCK_0000_START] タイトルテキスト [BLOCK_0000_END]
[BLOCK_0001_START] 段落1（文脈を考慮） [BLOCK_0001_END]
[BLOCK_0002_START] 段落2（前の段落とのつながり） [BLOCK_0002_END]
```

### 3. マーカーで分割して各ブロックに戻す

```python
# マーカーを使って元のブロック構造に戻す
Block 0 → タイトルテキスト
Block 1 → 段落1（文脈を考慮）
Block 2 → 段落2（前の段落とのつながり）
```

---

## 📊 使い方

### 基本的な使い方（推奨）

```cmd
python main.py paper.pdf --translate
```

**デフォルト設定**:
- セクションサイズ: 3000文字
- 見出しで自動的にセクション分割

---

### セクションサイズを変更

より大きな文脈:
```cmd
python main.py paper.pdf --translate --section-size 5000
```

**効果**:
- より多くの段落をまとめて翻訳
- 文脈がより広く保持される
- ただし翻訳時間が増加

---

より小さな文脈:
```cmd
python main.py paper.pdf --translate --section-size 1500
```

**効果**:
- セクションが細かく分割
- 翻訳速度が向上
- ただし文脈がやや狭まる

---

## 🎯 最適なセクションサイズ

### 短い論文（10ページ以下）

```cmd
python main.py paper.pdf --translate --section-size 5000
```

**理由**:
- 論文全体が短いので大きめのセクション
- 文脈を広く保持

---

### 中程度の論文（10-30ページ）

```cmd
python main.py paper.pdf --translate --section-size 3000
```

**理由**:
- バランスが良い（デフォルト）
- ほとんどの論文で最適

---

### 長い論文（30ページ以上）

```cmd
python main.py paper.pdf --translate --section-size 2000
```

**理由**:
- セクションを小さめに
- メモリ・時間を節約
- それでも文脈は保持

---

## 📝 翻訳品質の比較

### ブロック単位翻訳（旧方式）

```
Original:
[Block 1] Deep learning has revolutionized AI.
[Block 2] It enables machines to learn from data.
[Block 3] This approach has many applications.

Translation:
[Block 1] 深層学習はAIに革命をもたらした。
[Block 2] それは機械がデータから学習することを可能にする。
[Block 3] このアプローチは多くの応用がある。
```

**問題**:
- "それ" が何を指すか不明確
- "このアプローチ" が唐突

---

### セクション単位翻訳（新方式）

```
Original (Section):
Deep learning has revolutionized AI.
It enables machines to learn from data.
This approach has many applications.

Translation (Section):
深層学習はAIに革命をもたらした。
深層学習により、機械がデータから学習することが可能になる。
この深層学習アプローチには多くの応用がある。
```

**改善**:
- ✅ "深層学習により" と明示
- ✅ "この深層学習アプローチ" と具体的
- ✅ 自然な日本語

---

## 🔍 内部動作

### ステップ1: セクション分割

```
PDF → 1055ブロック

↓ グループ化

Section 1: Title + Abstract (5ブロック, 500文字)
Section 2: 1. Introduction (15ブロック, 2800文字)
Section 3: 2. Related Work (20ブロック, 2900文字)
Section 4: 3. Method Part 1 (18ブロック, 3000文字)
Section 5: 3. Method Part 2 (17ブロック, 2700文字)
...

合計: 50セクション
```

---

### ステップ2: セクション翻訳

```
[セクション 1/50] 5ブロック
   🔒 保護: 10個 (MATH:5, REF:3, TERM:2)
   ✅ DeepL使用
   🔓 復元完了 (使用エンジン: DeepL)

[セクション 2/50] 15ブロック
   🔒 保護: 25個 (MATH:10, REF:8, TERM:7)
   ✅ DeepL使用
   🔓 復元完了 (使用エンジン: DeepL)

...
```

---

### ステップ3: ブロック分配

```
セクション2の翻訳結果:
[BLOCK_0005_START] はじめに [BLOCK_0005_END]
[BLOCK_0006_START] 近年、深層学習... [BLOCK_0006_END]
[BLOCK_0007_START] この技術は... [BLOCK_0007_END]
...

↓ マーカーで分割

Block 5 → はじめに
Block 6 → 近年、深層学習...
Block 7 → この技術は...
```

---

## ⚙️ カスタマイズ

### プロンプト調整

より学術的な文体:

`src/translation/translator.py` を編集:

```python
prompt = f"""あなたは学術論文の翻訳者です。

重要なルール:
1. である調で統一
2. 学術的で格調高い表現を使用
3. 前後の文脈を踏まえた一貫性のある翻訳
4. 段落間のつながりを自然に

【英文】
{text}

【日本語訳】"""
```

---

### セクション分割ルール

より細かく分割:

`src/pipeline.py` を編集:

```python
def _group_into_sections(self, blocks):
    # 見出し2（subsection）でも分割
    if block.type in ['heading1', 'heading2']:
        sections.append(current_section)
        current_section = []
```

---

## 📊 パフォーマンス

### 翻訳時間

| セクションサイズ | セクション数 | 翻訳時間 |
|-----------------|-------------|---------|
| 1500文字 | 70セクション | 約40分 |
| 3000文字 | 35セクション | 約20分 |
| 5000文字 | 21セクション | 約12分 |

**Note**: DeepL使用時の目安

---

### 品質

| セクションサイズ | 文脈保持 | 自然さ |
|-----------------|---------|--------|
| 1500文字 | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| 3000文字 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 5000文字 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

**推奨**: 3000文字（バランスが最適）

---

## ✅ 確認方法

翻訳後のHTMLで確認:

### チェックポイント

1. **代名詞の自然さ**
   ```
   ❌ それは精度を向上させる
   ✅ この手法は精度を向上させる
   ```

2. **段落間のつながり**
   ```
   ❌ 実験を行った。結果を示す。
   ✅ 実験を行った。以下、その結果を示す。
   ```

3. **専門用語の一貫性**
   ```
   ❌ ニューラルネット...神経網...
   ✅ ニューラルネットワーク（統一）
   ```

4. **文脈の流れ**
   ```
   ❌ 唐突な話題転換
   ✅ スムーズな展開
   ```

---

## 🎯 まとめ

### v2の改善点

| 項目 | v1（ブロック単位） | v2（セクション単位） |
|------|-------------------|-------------------|
| 文脈保持 | ❌ 各ブロック独立 | ✅ セクション全体 |
| 代名詞 | ❌ 不自然 | ✅ 自然 |
| つながり | ❌ 途切れる | ✅ 滑らか |
| 翻訳時間 | 速い | やや遅い |
| 品質 | 低〜中 | 高 |

### 推奨設定

```cmd
# 最高品質（推奨）
python main.py paper.pdf --translate --section-size 3000

# 高速（品質もまずまず）
python main.py paper.pdf --translate --section-size 2000

# 最高品質（時間がかかる）
python main.py paper.pdf --translate --section-size 5000
```

---

これで**読みやすく自然な翻訳**が実現できます 🎉
