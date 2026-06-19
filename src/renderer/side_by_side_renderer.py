"""
Side-by-Side Renderer
左: 元PDFのページ画像（ブロック位置にハイライト）
右: 翻訳テキスト（ブロック単位・クリックで対応箇所を強調）
"""
import fitz
import base64
from typing import List, Optional
from ..parser.pdf_document import PDFDocument, BlockType, Page, Block


class SideBySideRenderer:
    """
    左右分割表示レンダラー

    左: 元PDFのページ画像（各ブロックの位置に番号ラベル）
    右: 翻訳済みテキスト（同じ番号ラベル付き）

    ブロック番号で1対1対応するので、ページ長の違いによるズレが生じない。
    """

    def __init__(self, pdf_path: str, dpi: int = 150):
        self.pdf_path = pdf_path
        self.dpi = dpi

    # ------------------------------------------------------------------ #
    # 公開API
    # ------------------------------------------------------------------ #

    def render(self, doc: PDFDocument, output_path: str) -> str:
        print("📷 PDFページを画像に変換中...")
        page_images = self._pdf_to_images()
        print(f"   ✅ {len(page_images)}ページ変換完了")

        html = self._build_html(doc, page_images)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        return html

    # ------------------------------------------------------------------ #
    # PDF → base64
    # ------------------------------------------------------------------ #

    def _pdf_to_images(self) -> List[dict]:
        """各ページを {data_uri, width_pt, height_pt} で返す"""
        pdf = fitz.open(self.pdf_path)
        zoom = self.dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        result = []

        try:
            for page in pdf:
                pix = page.get_pixmap(matrix=mat)
                data = base64.b64encode(pix.tobytes("png")).decode()
                result.append({
                    "src": f"data:image/png;base64,{data}",
                    "width_pt":  page.rect.width,
                    "height_pt": page.rect.height,
                })
        finally:
            pdf.close()
        return result

    # ------------------------------------------------------------------ #
    # HTML
    # ------------------------------------------------------------------ #

    def _build_html(self, doc: PDFDocument, page_images: List[dict]) -> str:
        title = doc.metadata.get("title", "翻訳論文")
        pages_html = "\n".join(
            self._build_page(page, page_images, doc)
            for page in doc.pages
        )
        return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{self._esc(title)} — 原文対照</title>

<script id="MathJax-script" async
        src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
<style>{self._css()}</style>
</head>
<body>
<header class="site-header">
  <div class="header-inner">
    <h1>{self._esc(title)}</h1>
    <span class="badge">原文 ↔ 翻訳 対照表示</span>
    <span class="hint">ブロックをクリックすると対応箇所が強調されます</span>
  </div>
</header>
<main class="pages">
{pages_html}
</main>
<footer class="site-footer">学術論文翻訳システム v2.0</footer>
<script>{self._js()}</script>
</body>
</html>"""

    def _build_page(self, page: Page, page_images: List[dict], doc: PDFDocument) -> str:
        idx = page.number - 1
        img_info = page_images[idx] if idx < len(page_images) else None

        # 翻訳対象ブロックだけ抽出（ヘッダー・フッター除外）
        blocks = [
            b for b in page.blocks
            if b.type not in (BlockType.HEADER, BlockType.FOOTER)
        ]

        left_html  = self._build_left(page, blocks, img_info)
        right_html = self._build_right(page, blocks)

        return f"""<section class="spread" id="page-{page.number}">
  <div class="page-label">Page {page.number}</div>
  <div class="columns">
    <div class="col col-original">{left_html}</div>
    <div class="col col-translated">{right_html}</div>
  </div>
</section>"""

    # ---- 左カラム：PDF画像 + ブロック位置オーバーレイ ---- #

    def _build_left(self, page: Page, blocks: List[Block], img_info: Optional[dict]) -> str:
        if not img_info:
            return "<div class='no-image'>画像なし</div>"

        w_pt = img_info["width_pt"]
        h_pt = img_info["height_pt"]

        # ブロックごとにオーバーレイ要素を生成
        overlays = []
        for i, block in enumerate(blocks):
            bid = f"p{page.number}_b{i}"
            # パーセント座標に変換
            x  = block.bbox.x0 / w_pt * 100
            y  = block.bbox.y0 / h_pt * 100
            w  = (block.bbox.x1 - block.bbox.x0) / w_pt * 100
            h  = (block.bbox.y1 - block.bbox.y0) / h_pt * 100
            overlays.append(
                f'<div class="overlay-block" id="ol-{bid}" data-bid="{bid}"'
                f' style="left:{x:.2f}%;top:{y:.2f}%;width:{w:.2f}%;height:{h:.2f}%">'
                f'<span class="block-num">{i + 1}</span></div>'
            )

        return f"""<div class="pdf-wrapper">
  <img src="{img_info['src']}" alt="Page {page.number}" class="pdf-page-img">
  <div class="overlay-container">
    {''.join(overlays)}
  </div>
</div>"""

    # ---- 右カラム：翻訳テキスト ---- #

    def _build_right(self, page: Page, blocks: List[Block]) -> str:
        if not blocks:
            return "<p class='empty'>（テキストなし）</p>"

        parts = []
        for i, block in enumerate(blocks):
            bid = f"p{page.number}_b{i}"
            cls = block.type.value

            if block.type == BlockType.EQUATION and self._looks_like_real_equation(block.content):
                raw = block.content
                if not raw.startswith("$"):
                    raw = f"$${raw}$$"
                inner = raw
            else:
                # equation でも英語本文が多い場合は通常テキスト扱い
                # （MathJax がスペースを除去して単語が繋がるのを防ぐ）
                inner = self._esc(block.content)

            parts.append(
                f'<div class="block {cls}" id="tr-{bid}" data-bid="{bid}">'
                f'<span class="block-num">{i + 1}</span>'
                f'<span class="block-text">{inner}</span>'
                f'</div>'
            )

        return "\n".join(parts)

    @staticmethod
    def _looks_like_real_equation(text: str) -> bool:
        """
        本物の数式か判定（MathJax処理してよいか）。

        英単語（4文字以上）が多いテキストは本文の可能性が高く、
        MathJax に渡すとスペースが除去され単語が繋がってしまうため、
        通常テキストとして扱う。
        """
        import re
        word_count = len(re.findall(r'[A-Za-z]{4,}', text))
        return word_count < 8

    # ------------------------------------------------------------------ #
    # CSS
    # ------------------------------------------------------------------ #

    def _css(self) -> str:
        return """
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'Noto Sans JP','Hiragino Kaku Gothic Pro','Yu Gothic',Meiryo,sans-serif;
  background: #e8e8e8;
  color: #222;
}

/* ヘッダー */
.site-header {
  background: #2c3e50;
  color: #fff;
  padding: 12px 24px;
  position: sticky;
  top: 0;
  z-index: 200;
  box-shadow: 0 2px 8px rgba(0,0,0,.4);
}
.header-inner { display:flex; align-items:center; gap:14px; max-width:1700px; margin:0 auto; }
.header-inner h1 { font-size:1rem; font-weight:700; flex:1; }
.badge { background:#3498db; border-radius:4px; padding:3px 10px; font-size:.75rem; white-space:nowrap; }
.hint  { font-size:.72rem; color:#aac; white-space:nowrap; }

/* ページ一覧 */
.pages { max-width:1700px; margin:0 auto; padding:24px 16px; display:flex; flex-direction:column; gap:32px; }

/* スプレッド */
.spread { background:#fff; border-radius:8px; box-shadow:0 2px 12px rgba(0,0,0,.15); overflow:hidden; }
.page-label { background:#2c3e50; color:#fff; font-size:.78rem; padding:4px 14px; letter-spacing:.05em; }

/* 2カラム */
.columns { display:grid; grid-template-columns:1fr 1fr; align-items:start; gap:0; }

/* 左: PDF画像 */
.col-original {
  border-right: 2px solid #ddd;
  background: #f5f5f5;
  padding: 12px;
  box-sizing: border-box;
  min-width: 0;            /* グリッドアイテムが縮みすぎるのを防ぐ */
}

/* PDF + オーバーレイの親 */
.pdf-wrapper {
  position: relative;
  display: block;          /* inline-block をやめ、確実に幅100%に */
  width: 100%;
  line-height: 0;          /* inline画像下の余白を除去 */
}
.pdf-page-img {
  width: 100%;
  height: auto;
  display: block;
}

/* オーバーレイコンテナ（画像に重ねる）*/
.overlay-container {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

/* 各ブロックのオーバーレイ枠 */
.overlay-block {
  position: absolute;
  border: 1.5px solid rgba(52, 152, 219, 0);  /* 通常は透明 */
  border-radius: 2px;
  cursor: pointer;
  pointer-events: all;
  transition: background .15s, border-color .15s;
}
.overlay-block:hover,
.overlay-block.active {
  background: rgba(52,152,219,.15);
  border-color: #3498db;
}
.overlay-block.active { background: rgba(52,152,219,.25); border-color:#2980b9; }

/* ブロック番号バッジ（左上） */
.overlay-block .block-num {
  position: absolute;
  top: -1px;
  left: -1px;
  background: #3498db;
  color: #fff;
  font-size: 9px;
  line-height: 1;
  padding: 1px 3px;
  border-radius: 0 0 3px 0;
  opacity: 0;
  transition: opacity .15s;
}
.overlay-block:hover .block-num,
.overlay-block.active .block-num { opacity: 1; }

/* 右: 翻訳テキスト */
.col-translated { padding: 18px 22px; line-height: 1.9; }

/* 翻訳ブロック */
.block {
  display: flex;
  gap: 6px;
  align-items: baseline;
  margin-bottom: 10px;
  padding: 4px 6px;
  border-radius: 4px;
  cursor: pointer;
  transition: background .15s;
  word-break: break-word;
}
.block:hover,
.block.active { background: #eaf4fb; }
.block.active  { background: #d6eaf8; outline: 1px solid #3498db; }

/* 右側の番号バッジ */
.block .block-num {
  flex-shrink: 0;
  background: #bdc3c7;
  color: #fff;
  font-size: 9px;
  border-radius: 3px;
  padding: 1px 4px;
  line-height: 1.4;
  margin-top: 4px;
}
.block:hover .block-num,
.block.active .block-num { background: #3498db; }

.block-text { flex: 1; }

/* タイプ別スタイル */
.block.title    { font-size:1.25em; font-weight:700; color:#1a252f; margin-bottom:16px; }
.block.abstract { background:#eaf4fb; border-left:4px solid #3498db; padding:10px 14px; font-size:.94em; }
.block.heading1 { font-size:1.15em; font-weight:700; color:#2c3e50; border-bottom:2px solid #3498db; padding-bottom:4px; margin-top:18px; }
.block.heading2 { font-size:1.05em; font-weight:700; color:#2c3e50; margin-top:14px; }
.block.heading3 { font-weight:700; color:#34495e; margin-top:10px; }
.block.paragraph { text-align:justify; color:#2c3e50; }
.block.equation  { justify-content:center; text-align:center; background:#f8f8f8; }
.block.caption   { font-size:.88em; font-style:italic; color:#666; }
.block.reference { font-size:.82em; color:#555; }

.no-image, .empty { color:#bbb; font-style:italic; font-size:.9rem; padding:20px; }

.site-footer { text-align:center; padding:16px; font-size:.8rem; color:#888;
  background:#fff; border-top:1px solid #ddd; margin-top:24px; }

/* レスポンシブ */
@media (max-width: 860px) {
  .columns { grid-template-columns:1fr; }
  .col-original { border-right:none; border-bottom:2px solid #ddd; }
}

/* 印刷 */
@media print {
  .site-header, .site-footer { display:none; }
  .spread { page-break-after:always; box-shadow:none; }
  .columns { grid-template-columns:1fr 1fr; }
  .overlay-block { display:none; }
}
"""

    # ------------------------------------------------------------------ #
    # JavaScript（クリックで対応ブロックを強調）
    # ------------------------------------------------------------------ #

    def _js(self) -> str:
        return """
(function () {
  let activeId = null;

  function activate(bid) {
    // 前のアクティブを解除
    if (activeId) {
      const ol = document.getElementById('ol-' + activeId);
      const tr = document.getElementById('tr-' + activeId);
      if (ol) ol.classList.remove('active');
      if (tr) tr.classList.remove('active');
    }

    if (bid === activeId) {
      activeId = null;
      return;
    }

    activeId = bid;
    const ol = document.getElementById('ol-' + bid);
    const tr = document.getElementById('tr-' + bid);
    if (ol) {
      ol.classList.add('active');
      ol.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    if (tr) {
      tr.classList.add('active');
      tr.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }

  // 左の画像オーバーレイをクリック
  document.querySelectorAll('.overlay-block').forEach(el => {
    el.addEventListener('click', () => activate(el.dataset.bid));
  });

  // 右の翻訳ブロックをクリック
  document.querySelectorAll('.block[data-bid]').forEach(el => {
    el.addEventListener('click', () => activate(el.dataset.bid));
  });
})();
"""

    @staticmethod
    def _esc(text: str) -> str:
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))

