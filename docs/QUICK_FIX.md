# とぎれとぎれ問題の解決

## 🐛 問題

翻訳文が以下のようになっている:

```
SATソルバーのヒューリスティックのうち、どれが#SATでの使用に適しているかを特定すること
本研究の主要な目標の一つは、Cachet自体の性能向上にとどまらず、
[10]において、学習された節を含むコンポーネント間の含意を制御することである。
技術に加え、より自由度が高く、かつ妥当性を保った手法の影響についても検討する。
```

**問題点**:
- 文が途中で切れている
- 順序が入れ替わっている
- 段落の構造が崩れている

---

## 🔧 解決方法

### 方法1: セクションサイズを大きくする（即効）

```cmd
python main.py paper.pdf --translate --section-size 8000
```

**効果**:
- より多くの段落をまとめて翻訳
- 文脈がより広く保持
- 順序が保たれやすい

**推奨値**:
- 短い論文: `--section-size 10000`
- 標準的な論文: `--section-size 8000`
- 長い論文: `--section-size 5000`

---

### 方法2: 既に翻訳済みの場合

既存のJSONから再生成:

```cmd
# 元のPDFから再翻訳
python main.py paper.pdf --translate --section-size 8000
```

**完全にやり直し**が必要です（セクション分割方法が変わるため）

---

### 方法3: ページ単位翻訳（最も安定）

```cmd
# 開発中（次のアップデートで追加予定）
python main.py paper.pdf --translate --page-mode
```

各ページをまとめて翻訳→最も安定

---

## 📊 セクションサイズの比較

| サイズ | 文脈 | 安定性 | 速度 |
|--------|------|--------|------|
| 1500 | 狭い | ⭐⭐ | 速い |
| 3000 | 中程度 | ⭐⭐⭐ | 普通 |
| 5000 | 広い | ⭐⭐⭐⭐ | やや遅い |
| 8000 | とても広い | ⭐⭐⭐⭐⭐ | 遅い |

**推奨**: `--section-size 8000`

---

## 🎯 実行例

### ステップ1: 既存の翻訳を削除

```cmd
del paper_translated.json
del paper_translated.html
```

### ステップ2: 大きなセクションサイズで再翻訳

```cmd
python main.py paper.pdf --translate --section-size 8000
```

### ステップ3: HTMLで確認

```cmd
# ブラウザで開く
paper_translated_layout.html
```

---

## ✅ 期待される改善

### Before（セクションサイズ 3000）

```
SATソルバーのヒューリスティックのうち、どれが#SATでの使用に適しているかを特定すること
本研究の主要な目標の一つは、Cachet自体の性能向上にとどまらず、
[10]において、学習された節を含むコンポーネント間の含意を制御することである。
```

❌ 文が途切れている

---

### After（セクションサイズ 8000）

```
本研究の主要な目標の一つは、Cachet自体の性能向上にとどまらず、SATソルバーのヒューリスティックのうち、
どれが#SATでの使用に適しているかを特定することである。我々は、分岐ヒューリスティック、
バックトラッキング手法、ランダム化、コンポーネント選択戦略、変数選択技術など、幅広い異なる手法を検討する。
```

✅ 自然な流れ

---

## 🔍 原因

### 問題の根本原因

1. **セクションが小さすぎる**
   - 3000文字では段落の途中で切れる
   - 文脈が途切れる

2. **段落の分割失敗**
   - 段落マーカーが正しく保持されない
   - 順序が入れ替わる

---

## 💡 恒久的な解決策

次回のアップデートで以下を実装予定:

### 1. ページ単位翻訳モード

```cmd
python main.py paper.pdf --translate --page-mode
```

各ページを丸ごと翻訳→最も安定

---

### 2. 文境界の尊重

```python
# 文の途中でセクション分割しない
if current_length > max_length:
    # 次の文末まで待つ
    if not text.endswith('.'):
        continue
```

---

### 3. より堅牢なマーカー

```
### PARAGRAPH_001 ###
...
### PARAGRAPH_002 ###
...
```

番号ベースで確実に復元

---

## 🚀 今すぐできること

### 最も効果的な方法

```cmd
python main.py paper.pdf --translate --section-size 8000
```

これで**ほとんどの問題が解決**します。

---

### セクションサイズの決め方

```python
# 論文の総文字数を確認
import fitz
doc = fitz.open("paper.pdf")
total_chars = sum(len(page.get_text()) for page in doc)
print(f"総文字数: {total_chars}")

# セクション数の目安
section_size = 8000
section_count = total_chars // section_size
print(f"セクション数: {section_count}")
```

**理想的なセクション数**: 10-50個

---

## 📝 チェックリスト

翻訳後に確認:

- [ ] 文が途中で切れていない
- [ ] 順序が自然
- [ ] 段落の構造が保たれている
- [ ] 代名詞が適切
- [ ] 全体の流れが滑らか

すべて ✅ になるまで `--section-size` を調整

---

## ⚙️ 推奨設定

```cmd
# 短い論文（10ページ以下）
python main.py paper.pdf --translate --section-size 10000

# 標準的な論文（10-30ページ）
python main.py paper.pdf --translate --section-size 8000

# 長い論文（30-50ページ）
python main.py paper.pdf --translate --section-size 5000

# 非常に長い論文（50ページ以上）
python main.py paper.pdf --translate --section-size 3000
```

---

これで自然な翻訳が実現できます！
