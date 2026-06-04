"""
PDF Structure Parser
PDFから構造を抽出してPDFDocumentを生成
"""
import fitz  # PyMuPDF
import re
from typing import List, Dict, Tuple, Optional
from pathlib import Path

from .pdf_document import (
    PDFDocument, Page, Block, Figure, Table,
    BlockType, BoundingBox, Style,
    merge_adjacent_blocks, calculate_reading_order
)


class PDFStructureParser:
    """
    PDF構造解析器
    
    PyMuPDFを使ってPDFを解析し、
    PDFDocumentオブジェクトを生成する。
    """

    # フォントサイズ比による分類しきい値（本文平均に対する倍率）
    TITLE_FONT_RATIO = 1.5       # タイトル
    HEADING_FONT_RATIO = 1.05    # 見出し
    HEADING1_RATIO = 1.3         # 大見出し
    HEADING2_RATIO = 1.15        # 中見出し
    HEADER_FOOTER_FONT_RATIO = 0.75  # ヘッダー/フッター（小フォント）

    # 位置しきい値（ページ高さに対する比率）
    TITLE_TOP_ZONE = 0.3         # タイトルはページ上部30%以内
    HEADER_ZONE = 0.08           # ヘッダー帯
    FOOTER_ZONE = 0.92           # フッター帯

    HEADER_FOOTER_MAX_WORDS = 8  # ヘッダー/フッターと見なす最大単語数
    HEADING_MAX_CHARS = 100      # 見出しと見なす最大文字数
    DEFAULT_AVG_FONT_SIZE = 11.0

    def __init__(self):
        self.avg_font_size: float = self.DEFAULT_AVG_FONT_SIZE
        self.avg_line_height: float = self.DEFAULT_AVG_FONT_SIZE * 1.2

    def parse(self, pdf_path: str) -> PDFDocument:
        """PDFを解析して PDFDocument を返す"""
        # 再利用に備えて統計値を初期化
        self.avg_font_size = self.DEFAULT_AVG_FONT_SIZE
        self.avg_line_height = self.DEFAULT_AVG_FONT_SIZE * 1.2

        doc = PDFDocument()

        pdf_doc = fitz.open(pdf_path)
        try:
            # メタデータを抽出
            self._extract_metadata(pdf_doc, doc)

            # === 1パス目: 各ページの blocks_data を1回だけ取得し、
            #     フォント統計とページ解析を同時に行う ===
            all_font_sizes: list[float] = []
            page_blocks_cache = []  # (pdf_page, blocks_data) を保持

            for page_num in range(len(pdf_doc)):
                pdf_page = pdf_doc[page_num]
                blocks_data = pdf_page.get_text("dict")["blocks"]  # ★1ページにつき1回だけ
                page_blocks_cache.append((pdf_page, blocks_data))

                # フォントサイズを収集
                for bd in blocks_data:
                    if bd["type"] == 0:
                        for line in bd.get("lines", []):
                            for span in line.get("spans", []):
                                all_font_sizes.append(span["size"])

            # フォント統計を確定（ページ解析の前に確定させる）
            if all_font_sizes:
                self.avg_font_size = sum(all_font_sizes) / len(all_font_sizes)
                self.avg_line_height = self.avg_font_size * 1.2

            # === 2パス目: 取得済み blocks_data を使ってページ解析 ===
            for page_num, (pdf_page, blocks_data) in enumerate(page_blocks_cache):
                page = self._parse_page(pdf_page, page_num, blocks_data)
                doc.add_page(page)
        finally:
            pdf_doc.close()

        # 後処理（ブロック分類・キャプション関連付け）
        self._post_process(doc)

        return doc

    def _extract_metadata(self, pdf_doc, doc: PDFDocument):
        """メタデータを抽出"""
        metadata = pdf_doc.metadata
        doc.metadata = {
            "title": metadata.get("title", "Untitled"),
            "authors": metadata.get("author", "").split(", ") if metadata.get("author") else [],
            "subject": metadata.get("subject", ""),
            "keywords": metadata.get("keywords", ""),
            "producer": metadata.get("producer", ""),
            "creator": metadata.get("creator", ""),
            "creation_date": metadata.get("creationDate", ""),
            "page_count": len(pdf_doc)
        }
    
    def _parse_page(self, pdf_page, page_num: int, blocks_data: list) -> Page:
        """
        1ページを解析。

        blocks_data は呼び出し側で取得済みの get_text("dict")["blocks"] を渡す
        （ページごとの get_text 呼び出しを1回に抑えるため）。
        """
        page = Page(
            number=page_num + 1,
            width=pdf_page.rect.width,
            height=pdf_page.rect.height
        )

        for block_idx, block_data in enumerate(blocks_data):
            if block_data["type"] == 0:  # テキストブロック
                blocks = self._process_text_block(block_data, page_num, block_idx)
                for block in blocks:
                    page.add_block(block)

            elif block_data["type"] == 1:  # 埋め込み画像ブロック
                figure = self._process_image_block(block_data, page_num, block_idx)
                if figure:
                    page.add_figure(figure)

        # ベクター描画領域を図/表として追加
        self._detect_vector_figures(pdf_page, page, page_num)

        # ブロックをマージ（この時点では全て UNKNOWN なので
        # フォントサイズ・位置・配置で結合判定する）
        page.blocks = merge_adjacent_blocks(page.blocks)

        # 読み順でソート
        page.blocks = calculate_reading_order(page.blocks)

        return page
    
    def _detect_vector_figures(self, pdf_page, page: Page, page_num: int):
        """
        ベクター描画を図または表として検出。

        戦略:
        1. 水平・垂直の直線が格子を形成 → Table
        2. それ以外の描画クラスタ（グラフ等） → Figure
        """
        try:
            drawings = pdf_page.get_drawings()
        except Exception:
            return

        if not drawings:
            return

        h_lines: list[tuple] = []  # (x0, y, x1)  水平線
        v_lines: list[tuple] = []  # (x, y0, y1)  垂直線
        other_rects: list = []     # その他の矩形/曲線パス

        for d in drawings:
            # --- 直線セグメントを分類 ---
            for item in d.get("items", []):
                kind = item[0]
                if kind == "l":           # 線分
                    p1, p2 = item[1], item[2]
                    dx = abs(p2.x - p1.x)
                    dy = abs(p2.y - p1.y)
                    if dy < 1.5 and dx > 5:          # ほぼ水平
                        h_lines.append((min(p1.x, p2.x), (p1.y + p2.y) / 2, max(p1.x, p2.x)))
                    elif dx < 1.5 and dy > 5:        # ほぼ垂直
                        v_lines.append(((p1.x + p2.x) / 2, min(p1.y, p2.y), max(p1.y, p2.y)))
                elif kind in ("re", "qu"):  # 矩形 / 四辺形
                    r = item[1]
                    # Quad は .rect で Rect に変換
                    if hasattr(r, "rect"):
                        r = r.rect
                    if hasattr(r, "width") and r.width > 5 and r.height > 5:
                        other_rects.append(r)
            # 描画全体の rect も収集（面積のある形状のみ）
            r = d.get("rect")
            if r is not None:
                if hasattr(r, "rect"):   # Quad → Rect
                    r = r.rect
                if hasattr(r, "get_area") and r.get_area() > 200:
                    other_rects.append(r)

        # --- 表候補: 水平線・垂直線の格子を検出 ---
        page_area = page.width * page.height
        MAX_AREA_RATIO = 0.7   # ページ面積の70%を超える領域は図表とみなさない

        table_bbox = self._detect_table_from_lines(h_lines, v_lines)
        registered_bboxes: list[tuple] = []

        for bbox_tuple in table_bbox:
            x0, y0, x1, y1 = bbox_tuple
            if x1 - x0 < 20 or y1 - y0 < 20:
                continue
            # ページ全体に近い領域（罫線テンプレート・透かし）は除外
            if (x1 - x0) * (y1 - y0) > page_area * MAX_AREA_RATIO:
                continue
            if any(self._rects_overlap(x0, y0, x1, y1, *rb) for rb in registered_bboxes):
                continue
            if any(self._rects_overlap(x0, y0, x1, y1,
                                        fig.bbox.x0, fig.bbox.y0, fig.bbox.x1, fig.bbox.y1)
                   for fig in page.figures):
                continue
            tbl = Table(
                id=f"table_{page.number:03d}_{len(page.tables):04d}",
                bbox=BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1),
                rows=0, cols=0, cells=[],
                metadata={"page": page.number, "source": "vector_lines"}
            )
            page.add_table(tbl)
            registered_bboxes.append((x0, y0, x1, y1))

        # --- 図候補: その他の矩形クラスタ ---
        if not other_rects:
            return

        groups = self._cluster_rects(other_rects, gap=20)
        for group_idx, group_rects in enumerate(groups):
            x0 = min(r.x0 for r in group_rects)
            y0 = min(r.y0 for r in group_rects)
            x1 = max(r.x1 for r in group_rects)
            y1 = max(r.y1 for r in group_rects)
            if x1 - x0 < 30 or y1 - y0 < 30:
                continue
            # ページ全体に近い領域は除外（本文吸収を防ぐ）
            if (x1 - x0) * (y1 - y0) > page_area * MAX_AREA_RATIO:
                continue
            if any(self._rects_overlap(x0, y0, x1, y1, *rb) for rb in registered_bboxes):
                continue
            if any(self._rects_overlap(x0, y0, x1, y1,
                                        fig.bbox.x0, fig.bbox.y0, fig.bbox.x1, fig.bbox.y1)
                   for fig in page.figures):
                continue
            page.add_figure(Figure(
                id=f"figure_{page.number:03d}_{group_idx:04d}",
                bbox=BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1),
                image_data=b"",
                metadata={"page": page.number, "source": "vector"}
            ))
            registered_bboxes.append((x0, y0, x1, y1))

    def _cluster_rects(self, rects, gap: float = 20):
        """矩形をグループにクラスタリング（近接するものをまとめる）"""
        if not rects:
            return []

        groups = []
        used = [False] * len(rects)

        for i, r in enumerate(rects):
            if used[i]:
                continue
            group = [r]
            used[i] = True
            queue = [r]
            while queue:
                cur = queue.pop()
                for j, other in enumerate(rects):
                    if used[j]:
                        continue
                    if (cur.x0 - gap <= other.x1 and other.x0 - gap <= cur.x1 and
                            cur.y0 - gap <= other.y1 and other.y0 - gap <= cur.y1):
                        group.append(other)
                        used[j] = True
                        queue.append(other)
            groups.append(group)

        return groups

    def _detect_table_from_lines(
        self,
        h_lines: list,
        v_lines: list,
        snap: float = 4.0,
        min_rows: int = 2,
        min_cols: int = 2,
    ) -> list[tuple]:
        """
        水平線・垂直線の格子から表の bbox を返す。

        snap: 同一座標とみなす許容差 (pt)
        """
        if not h_lines or not v_lines:
            return []

        # Y座標でグルーピング（行の罫線）
        def snap_values(vals: list[float]) -> list[float]:
            if not vals:
                return []
            vals = sorted(vals)
            groups: list[list[float]] = [[vals[0]]]
            for v in vals[1:]:
                if v - groups[-1][-1] <= snap:
                    groups[-1].append(v)
                else:
                    groups.append([v])
            return [sum(g) / len(g) for g in groups]

        hy_vals = snap_values([ln[1] for ln in h_lines])
        vx_vals = snap_values([ln[0] for ln in v_lines])

        if len(hy_vals) < min_rows + 1 or len(vx_vals) < min_cols + 1:
            return []

        # 連続する水平線・垂直線が作るセルの矩形をグループ化
        # 全体を覆う 1 つの bbox を返す（表全体）
        x0 = min(vx_vals)
        x1 = max(vx_vals)
        y0 = min(hy_vals)
        y1 = max(hy_vals)

        # 余裕を見て少し広げる
        margin = 2
        return [(x0 - margin, y0 - margin, x1 + margin, y1 + margin)]
    
    @staticmethod
    def _rects_overlap(ax0, ay0, ax1, ay1, bx0, by0, bx1, by1, margin=10) -> bool:
        """2矩形が重なるか（marginを許容）"""
        return not (ax1 + margin < bx0 or bx1 + margin < ax0 or
                    ay1 + margin < by0 or by1 + margin < ay0)
    
    def _process_text_block(self, block_data: Dict, page_num: int, block_idx: int) -> List[Block]:
        """テキストブロックを処理 - ブロック全体を1つにまとめる"""
        lines = block_data.get("lines", [])
        if not lines:
            return []
        
        # ブロック全体のテキストを結合
        full_text = ""
        all_font_sizes = []
        all_font_names = []

        for line in lines:
            # スパンを結合。スパン境界で単語が繋がらないよう、
            # 直前が英数字・直後も英数字なら半角スペースを補う。
            line_text = ""
            for span in line.get("spans", []):
                t = span["text"]
                if (line_text and t and
                        line_text[-1].isalnum() and t[0].isalnum()):
                    # フォント切替などでスペースが失われたケースを補完
                    # ただし元テキストに既に空白があれば二重にしない
                    if not line_text.endswith(" ") and not t.startswith(" "):
                        line_text += ""  # PDFは通常スパン内に空白を保持するため補完しない
                line_text += t
                all_font_sizes.append(span["size"])
                all_font_names.append(span["font"])

            line_text = line_text.strip()
            if not line_text:
                continue

            # 行末ハイフン折り返し（exam- / ple → example）
            if full_text.endswith("-") and len(full_text) > 1:
                # ハイフン直前が英字のときのみ連結（範囲 "3-5" などは保護）
                if full_text[-2].isalpha():
                    full_text = full_text[:-1] + line_text + " "
                else:
                    full_text += line_text + " "
            else:
                full_text += line_text + " "

        full_text = full_text.strip()
        if not full_text:
            return []
        
        # このブロック内のフォントサイズ平均。span が無い稀なケースでは
        # parse() の1パス目で確定済みの self.avg_font_size をフォールバックに使う。
        avg_font_size = sum(all_font_sizes) / len(all_font_sizes) if all_font_sizes else self.avg_font_size
        primary_font = all_font_names[0] if all_font_names else ""
        
        is_bold = any("bold" in n.lower() or "heavy" in n.lower() for n in all_font_names)
        is_italic = any("italic" in n.lower() or "oblique" in n.lower() for n in all_font_names)
        
        style = Style(
            font_name=primary_font,
            font_size=avg_font_size,
            is_bold=is_bold,
            is_italic=is_italic
        )
        
        # ブロック全体のバウンディングボックス
        bbox = BoundingBox(
            x0=block_data["bbox"][0],
            y0=block_data["bbox"][1],
            x1=block_data["bbox"][2],
            y1=block_data["bbox"][3]
        )
        
        block = Block(
            id=f"block_{page_num:03d}_{block_idx:04d}",
            type=BlockType.UNKNOWN,
            bbox=bbox,
            content=full_text,
            style=style
        )
        
        return [block]
    
    def _process_image_block(self, block_data: Dict, page_num: int, block_idx: int) -> Optional[Figure]:
        """画像ブロックを処理"""
        bbox = BoundingBox(
            x0=block_data["bbox"][0],
            y0=block_data["bbox"][1],
            x1=block_data["bbox"][2],
            y1=block_data["bbox"][3]
        )
        
        # 画像データを抽出（空のプレースホルダ）
        # 実際の画像は別途抽出が必要
        figure = Figure(
            id=f"figure_{page_num:03d}_{block_idx:04d}",
            bbox=bbox,
            image_data=b"",  # 後で埋める
            metadata={"page": page_num + 1, "block_idx": block_idx}
        )
        
        return figure
    
    def _post_process(self, doc: PDFDocument):
        """後処理"""
        self._classify_blocks(doc)
        self._associate_captions(doc)

    def _classify_blocks(self, doc: PDFDocument):
        """ブロックタイプを分類"""
        for page in doc.pages:
            # 図・表の bbox（内部テキストを翻訳から除外するため）
            figure_bboxes = [(f.bbox.x0, f.bbox.y0, f.bbox.x1, f.bbox.y1) for f in page.figures]
            table_bboxes  = [(t.bbox.x0, t.bbox.y0, t.bbox.x1, t.bbox.y1) for t in page.tables]

            for block in page.blocks:
                if block.type != BlockType.UNKNOWN:
                    continue

                bx0, by0, bx1, by1 = (block.bbox.x0, block.bbox.y0,
                                       block.bbox.x1, block.bbox.y1)

                # 表の内部テキストは翻訳対象から除外（FOOTER として扱う）
                if any(self._block_inside(bx0, by0, bx1, by1, *tb) for tb in table_bboxes):
                    block.type = BlockType.FOOTER   # 非翻訳タイプで代用
                    block.metadata["inside_table"] = True
                    continue

                # 図の内部テキスト（ラベル等）も翻訳対象から除外
                if any(self._block_inside(bx0, by0, bx1, by1, *fb) for fb in figure_bboxes):
                    block.type = BlockType.FOOTER
                    block.metadata["inside_figure"] = True
                    continue

                # 通常の分類
                if self._is_title(block, page):
                    block.type = BlockType.TITLE
                elif self._is_abstract(block):
                    block.type = BlockType.ABSTRACT
                elif self._is_heading(block):
                    block.type = self._classify_heading_level(block)
                elif self._is_equation(block):
                    block.type = BlockType.EQUATION
                elif self._is_caption(block):
                    block.type = BlockType.CAPTION
                elif self._is_reference(block):
                    block.type = BlockType.REFERENCE
                elif self._is_code(block):
                    block.type = BlockType.CODE
                elif self._is_header_or_footer(block, page):
                    if block.bbox.y0 < page.height * 0.08:
                        block.type = BlockType.HEADER
                    else:
                        block.type = BlockType.FOOTER
                else:
                    block.type = BlockType.PARAGRAPH

    @staticmethod
    def _block_inside(bx0, by0, bx1, by1, tx0, ty0, tx1, ty1,
                      overlap_thresh: float = 0.6) -> bool:
        """
        ブロックが bbox の内部にあるか（重なり面積 overlap_thresh 以上）
        """
        ix0 = max(bx0, tx0)
        iy0 = max(by0, ty0)
        ix1 = min(bx1, tx1)
        iy1 = min(by1, ty1)
        if ix1 <= ix0 or iy1 <= iy0:
            return False
        inter = (ix1 - ix0) * (iy1 - iy0)
        block_area = max((bx1 - bx0) * (by1 - by0), 1)
        return (inter / block_area) >= overlap_thresh
    
    def _is_title(self, block: Block, page: Page) -> bool:
        """タイトル判定（ページ上部・大きいフォント・太字）"""
        return (
            page.number == 1 and
            block.bbox.y0 < page.height * self.TITLE_TOP_ZONE and
            block.style.font_size > self.avg_font_size * self.TITLE_FONT_RATIO and
            block.style.is_bold
        )

    def _is_abstract(self, block: Block) -> bool:
        """
        Abstract判定。

        「Abstract」見出し単体、または「Abstract」「Abstract.」「Abstract—」
        「Abstract:」で始まる短めのブロックのみを対象とする。
        長い段落の先頭にたまたま abstract があっても誤検知しないよう、
        先頭の数文字に限定して判定する。
        """
        text = block.content.strip()
        head = text[:12].lower()
        return bool(re.match(r'^abstract\b[\s.:—-]*', head))

    def _is_heading(self, block: Block) -> bool:
        """見出し判定"""
        return (
            block.style.is_bold and
            block.style.font_size > self.avg_font_size * self.HEADING_FONT_RATIO and
            len(block.content) < self.HEADING_MAX_CHARS
        )

    def _classify_heading_level(self, block: Block) -> BlockType:
        """見出しレベルを分類"""
        if block.style.font_size > self.avg_font_size * self.HEADING1_RATIO:
            return BlockType.HEADING1
        elif block.style.font_size > self.avg_font_size * self.HEADING2_RATIO:
            return BlockType.HEADING2
        else:
            return BlockType.HEADING3
    
    def _is_equation(self, block: Block) -> bool:
        """
        数式判定。

        短い本文（"Let x, y, z be reals." など）を誤って数式扱いしないよう、
        記号の割合と絶対数の両方を見る。テキストが長いほど高い割合を要求する。
        """
        text = block.content
        if len(text) == 0:
            return False

        # LaTeXコマンド・添字記号
        latex_count = len(re.findall(r'\\[a-zA-Z]+|[\{\}_\^]', text))
        # Unicode数学記号
        math_count = len(re.findall(
            r'[∑∏∫∂∇≤≥≠±×÷√∞∈∉⊂⊃∩∪∀∃αβγδεθλμπσφψω≈≅≡⊕⊗→↦]', text
        ))

        symbol_count = latex_count + math_count
        math_ratio = symbol_count / len(text)

        # 短文では割合が高くても誤判定しやすいので絶対数の下限も課す
        if len(text) <= 30:
            return math_ratio > 0.30 and symbol_count >= 4
        else:
            return math_ratio > 0.20 or symbol_count >= 8
    
    def _is_caption(self, block: Block) -> bool:
        """キャプション判定（Figure/Table/Algorithm/Listing + 小数点番号対応）"""
        text = block.content.strip()
        caption_pattern = r'^(Figure|Fig\.|Table|Tab\.|Algorithm|Listing|Scheme)\s+\d+(?:\.\d+)*'
        return bool(re.match(caption_pattern, text, re.IGNORECASE))
    
    def _is_reference(self, block: Block) -> bool:
        """参考文献判定"""
        text_lower = block.content.lower().strip()
        return text_lower.startswith("references") or text_lower.startswith("bibliography")
    
    def _is_code(self, block: Block) -> bool:
        """
        コード判定。

        モノスペースフォントだけで判定すると、本文がモノスペース系の論文で
        全ブロックがCODE化される。そこで「モノスペースフォント」かつ
        「コードらしい記号（{};=()）を一定割合含む」ことを条件にする。
        """
        font = block.style.font_name.lower()
        is_mono = "mono" in font or "courier" in font or "consol" in font
        if not is_mono:
            return False

        text = block.content
        if not text:
            return False
        code_chars = len(re.findall(r'[{};=()\[\]<>]', text))
        return (code_chars / len(text)) > 0.03
    
    def _is_header_or_footer(self, block: Block, page: Page) -> bool:
        """
        ヘッダー・フッター判定

        位置（上端8%以内 or 下端8%以内）かつ以下のどちらか:
        - テキストが短い（8単語以下）
        - フォントが本文平均の75%以下

        「8単語以下」は「mechanism during search ...」（14語）を除外しつつ
        「c」「Page 2」「2」などの典型的なヘッダーを捕捉する。
        """
        in_header_zone = block.bbox.y0 < page.height * self.HEADER_ZONE
        in_footer_zone = block.bbox.y1 > page.height * self.FOOTER_ZONE

        if not (in_header_zone or in_footer_zone):
            return False

        word_count = len(block.content.strip().split())
        is_short      = word_count <= self.HEADER_FOOTER_MAX_WORDS
        is_small_font = block.style.font_size < self.avg_font_size * self.HEADER_FOOTER_FONT_RATIO

        return is_short or is_small_font
    
    def _associate_captions(self, doc: PDFDocument):
        """
        キャプションと図表を関連付け。

        各キャプションに最も近い図表を選ぶ（最近傍選択）。
        同じカラムにある（X軸の重なりがある）ものだけを候補とし、
        マルチカラムレイアウトでの誤マッチを防ぐ。
        """
        CAPTION_GAP_PT = 40  # キャプションと図表の最大距離 (pt)

        for page in doc.pages:
            captions = page.get_blocks_by_type(BlockType.CAPTION)

            for caption in captions:
                cx0, cy0, cx1, cy1 = (caption.bbox.x0, caption.bbox.y0,
                                      caption.bbox.x1, caption.bbox.y1)

                best_target = None
                best_dist = CAPTION_GAP_PT + 1

                # 図との距離を計算（同カラム限定）
                for figure in page.figures:
                    if not self._x_overlap(cx0, cx1, figure.bbox.x0, figure.bbox.x1):
                        continue
                    dist = min(abs(cy0 - figure.bbox.y1), abs(cy1 - figure.bbox.y0))
                    if dist < best_dist:
                        best_dist = dist
                        best_target = ("figure", figure)

                # 表との距離を計算（同カラム限定）
                for table in page.tables:
                    if not self._x_overlap(cx0, cx1, table.bbox.x0, table.bbox.x1):
                        continue
                    dist = min(abs(cy0 - table.bbox.y1), abs(cy1 - table.bbox.y0))
                    if dist < best_dist:
                        best_dist = dist
                        best_target = ("table", table)

                if best_target:
                    kind, target = best_target
                    target.caption = caption
                    caption.metadata["is_figure_caption"] = True

    @staticmethod
    def _x_overlap(ax0: float, ax1: float, bx0: float, bx1: float,
                   margin: float = 10.0) -> bool:
        """2つの区間がX方向に重なるか（margin を許容）"""
        return ax0 - margin < bx1 and bx0 - margin < ax1


def main():
    """テスト"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python structure_parser.py <pdf_file>")
        return
    
    pdf_path = sys.argv[1]
    
    parser = PDFStructureParser()
    doc = parser.parse(pdf_path)
    
    print("="*60)
    print(f"Title: {doc.metadata['title']}")
    print(f"Pages: {len(doc.pages)}")
    print("="*60)
    
    stats = doc.get_statistics()
    print("\nStatistics:")
    for key, value in stats.items():
        if key == "block_types":
            print(f"\n  Block types:")
            for btype, count in value.items():
                print(f"    {btype}: {count}")
        else:
            print(f"  {key}: {value}")
    
    # JSONに保存
    output_path = Path(pdf_path).stem + "_structure.json"
    doc.to_json(output_path)
    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    main()
