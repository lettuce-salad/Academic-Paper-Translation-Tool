"""
PDF Document Model
PDFの完全な構造表現
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union
from enum import Enum
import json


class BlockType(Enum):
    """ブロックタイプ"""
    TITLE = "title"
    AUTHOR = "author"
    ABSTRACT = "abstract"
    HEADING1 = "heading1"
    HEADING2 = "heading2"
    HEADING3 = "heading3"
    PARAGRAPH = "paragraph"
    EQUATION = "equation"
    EQUATION_NUMBER = "equation_number"
    TABLE = "table"
    FIGURE = "figure"
    CAPTION = "caption"
    CODE = "code"
    REFERENCE = "reference"
    CITATION = "citation"
    FOOTER = "footer"
    HEADER = "header"
    LIST_ITEM = "list_item"
    UNKNOWN = "unknown"


@dataclass
class BoundingBox:
    """
    座標情報（PyMuPDF座標系: 左上原点）
    x0,y0 = 左上端（小）、x1,y1 = 右下端（大）
    y0 < y1（y0が上、y1が下）
    """
    x0: float  # 左端
    y0: float  # 上端（小さい値）
    x1: float  # 右端
    y1: float  # 下端（大きい値）
    
    @property
    def width(self) -> float:
        return self.x1 - self.x0
    
    @property
    def height(self) -> float:
        return self.y1 - self.y0
    
    @property
    def area(self) -> float:
        return self.width * self.height
    
    @property
    def center(self) -> tuple[float, float]:
        return ((self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2)
    
    def contains(self, x: float, y: float) -> bool:
        """点が矩形内にあるか"""
        return self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1
    
    def overlaps(self, other: 'BoundingBox') -> bool:
        """他の矩形と重なるか"""
        return not (self.x1 < other.x0 or self.x0 > other.x1 or
                   self.y1 < other.y0 or self.y0 > other.y1)
    
    def to_dict(self) -> Dict:
        return {
            "x0": self.x0,
            "y0": self.y0,
            "x1": self.x1,
            "y1": self.y1,
            "width": self.width,
            "height": self.height
        }


@dataclass
class Style:
    """スタイル情報"""
    font_name: str = ""
    font_size: float = 0.0
    font_color: str = "#000000"
    is_bold: bool = False
    is_italic: bool = False
    is_underline: bool = False
    line_height: float = 1.2
    
    def to_dict(self) -> Dict:
        return {
            "font_name": self.font_name,
            "font_size": self.font_size,
            "font_color": self.font_color,
            "is_bold": self.is_bold,
            "is_italic": self.is_italic,
            "is_underline": self.is_underline,
            "line_height": self.line_height
        }


@dataclass
class Block:
    """
    テキストブロック
    
    PDFの最小単位。座標とコンテンツを保持。
    翻訳後も座標は変更しない。
    """
    id: str
    type: BlockType
    bbox: BoundingBox
    content: str  # テキストまたはLaTeX（数式の場合）
    style: Style = field(default_factory=Style)
    metadata: Dict = field(default_factory=dict)
    
    # 翻訳関連
    original_content: Optional[str] = None  # 元のテキスト
    is_translated: bool = False
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            "id": self.id,
            "type": self.type.value,
            "bbox": self.bbox.to_dict(),
            "content": self.content,
            "original_content": self.original_content,
            "is_translated": self.is_translated,
            "style": self.style.to_dict(),
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Block':
        """辞書から復元"""
        bbox = BoundingBox(
            x0=data["bbox"]["x0"],
            y0=data["bbox"]["y0"],
            x1=data["bbox"]["x1"],
            y1=data["bbox"]["y1"]
        )
        
        style = Style(**data.get("style", {}))
        
        return cls(
            id=data["id"],
            type=BlockType(data["type"]),
            bbox=bbox,
            content=data["content"],
            original_content=data.get("original_content"),
            is_translated=data.get("is_translated", False),
            style=style,
            metadata=data.get("metadata", {}),
        )


@dataclass
class Figure:
    """図・画像"""
    id: str
    bbox: BoundingBox
    image_data: bytes  # PNG/JPEG data
    caption: Optional[Block] = None
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "bbox": self.bbox.to_dict(),
            "image_size": len(self.image_data),
            "has_caption": self.caption is not None,
            "caption": self.caption.to_dict() if self.caption else None,
            "metadata": self.metadata
        }


@dataclass
class Table:
    """表"""
    id: str
    bbox: BoundingBox
    rows: int
    cols: int
    cells: List[List[Block]]  # cells[row][col]
    caption: Optional[Block] = None
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "bbox": self.bbox.to_dict(),
            "rows": self.rows,
            "cols": self.cols,
            "cells": [[cell.to_dict() for cell in row] for row in self.cells],
            "caption": self.caption.to_dict() if self.caption else None,
            "metadata": self.metadata
        }


@dataclass
class Page:
    """
    1ページの情報

    座標系はPyMuPDF座標（左上原点）
    y0 < y1（y0が上端、y1が下端）
    """
    number: int  # 1始まり
    width: float  # pt
    height: float  # pt
    blocks: List[Block] = field(default_factory=list)
    figures: List[Figure] = field(default_factory=list)
    tables: List[Table] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    def add_block(self, block: Block):
        """ブロックを追加"""
        self.blocks.append(block)
    
    def add_figure(self, figure: Figure):
        """図を追加"""
        self.figures.append(figure)
    
    def add_table(self, table: Table):
        """表を追加"""
        self.tables.append(table)
    
    def get_blocks_by_type(self, block_type: BlockType) -> List[Block]:
        """指定タイプのブロックを取得"""
        return [b for b in self.blocks if b.type == block_type]
    
    def get_translatable_blocks(self) -> List[Block]:
        """翻訳対象ブロックを取得"""
        translatable_types = {
            BlockType.TITLE,
            BlockType.ABSTRACT,
            BlockType.HEADING1,
            BlockType.HEADING2,
            BlockType.HEADING3,
            BlockType.PARAGRAPH,
            BlockType.CAPTION,
            BlockType.LIST_ITEM
        }
        return [b for b in self.blocks if b.type in translatable_types]
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            "number": self.number,
            "width": self.width,
            "height": self.height,
            "blocks": [b.to_dict() for b in self.blocks],
            "figures": [f.to_dict() for f in self.figures],
            "tables": [t.to_dict() for t in self.tables],
            "metadata": self.metadata
        }


@dataclass
class PDFDocument:
    """
    PDFドキュメント全体
    
    構造と座標を完全に保持。
    翻訳後も同じレイアウトで出力できる。
    """
    pages: List[Page] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        """メタデータの初期化"""
        if "title" not in self.metadata:
            self.metadata["title"] = "Untitled"
        if "authors" not in self.metadata:
            self.metadata["authors"] = []
    
    def add_page(self, page: Page):
        """ページを追加"""
        self.pages.append(page)
    
    def get_page(self, page_number: int) -> Optional[Page]:
        """ページ番号でページを取得（1始まり）"""
        for page in self.pages:
            if page.number == page_number:
                return page
        return None
    
    def get_all_blocks(self) -> List[Block]:
        """全ページの全ブロックを取得"""
        all_blocks = []
        for page in self.pages:
            all_blocks.extend(page.blocks)
        return all_blocks
    
    def get_translatable_blocks(self) -> List[Block]:
        """翻訳対象の全ブロックを取得"""
        translatable = []
        for page in self.pages:
            translatable.extend(page.get_translatable_blocks())
        return translatable
    
    def get_statistics(self) -> Dict:
        """統計情報を取得"""
        all_blocks = self.get_all_blocks()
        
        type_counts = {}
        for block in all_blocks:
            type_name = block.type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        translatable_blocks = self.get_translatable_blocks()
        total_chars = sum(len(b.content) for b in translatable_blocks)
        
        return {
            "page_count": len(self.pages),
            "total_blocks": len(all_blocks),
            "translatable_blocks": len(translatable_blocks),
            "total_characters": total_chars,
            "block_types": type_counts,
            "figure_count": sum(len(p.figures) for p in self.pages),
            "table_count": sum(len(p.tables) for p in self.pages)
        }
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            "metadata": self.metadata,
            "statistics": self.get_statistics(),
            "pages": [p.to_dict() for p in self.pages]
        }
    
    def to_json(self, filepath: str):
        """JSON形式で保存"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, filepath: str) -> 'PDFDocument':
        """JSONから読み込み（figures/tablesも復元）"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        doc = cls(metadata=data.get("metadata", {}))
        
        for page_data in data.get("pages", []):
            page = Page(
                number=page_data["number"],
                width=page_data["width"],
                height=page_data["height"],
                metadata=page_data.get("metadata", {})
            )
            
            for block_data in page_data.get("blocks", []):
                block = Block.from_dict(block_data)
                page.add_block(block)
            
            # figures復元
            for fig_data in page_data.get("figures", []):
                bbox_d = fig_data.get("bbox", {})
                bbox = BoundingBox(
                    x0=bbox_d.get("x0", 0), y0=bbox_d.get("y0", 0),
                    x1=bbox_d.get("x1", 0), y1=bbox_d.get("y1", 0)
                )
                cap_data = fig_data.get("caption")
                caption = Block.from_dict(cap_data) if cap_data else None
                fig = Figure(
                    id=fig_data.get("id", ""),
                    bbox=bbox,
                    image_data=b"",
                    caption=caption,
                    metadata=fig_data.get("metadata", {})
                )
                page.add_figure(fig)
            
            # tables復元
            for tbl_data in page_data.get("tables", []):
                bbox_d = tbl_data.get("bbox", {})
                bbox = BoundingBox(
                    x0=bbox_d.get("x0", 0), y0=bbox_d.get("y0", 0),
                    x1=bbox_d.get("x1", 0), y1=bbox_d.get("y1", 0)
                )
                # cellsをList[List[Block]]に変換（JSON上はdictのリスト）
                raw_cells = tbl_data.get("cells", [])
                cells: List[List[Block]] = []
                for raw_row in raw_cells:
                    if isinstance(raw_row, list):
                        cells.append([
                            Block.from_dict(c) if isinstance(c, dict) else c
                            for c in raw_row
                        ])
                # captionを復元
                cap_data = tbl_data.get("caption")
                caption = Block.from_dict(cap_data) if cap_data else None
                tbl = Table(
                    id=tbl_data.get("id", ""),
                    bbox=bbox,
                    rows=tbl_data.get("rows", len(cells)),
                    cols=tbl_data.get("cols", max((len(r) for r in cells), default=0)),
                    cells=cells,
                    caption=caption,
                    metadata=tbl_data.get("metadata", {})
                )
                page.add_table(tbl)
            
            doc.add_page(page)
        
        return doc


# ユーティリティ関数

# 段落マージの閾値定数
MERGE_VERTICAL_THRESHOLD = 15.0   # 縦方向の近さ（pt）
MERGE_FONT_TOLERANCE = 0.5        # フォントサイズ差の許容（pt）
MERGE_HORIZONTAL_TOLERANCE = 20.0  # 横位置ずれの許容（pt）


def merge_adjacent_blocks(blocks: List[Block],
                          threshold: float = MERGE_VERTICAL_THRESHOLD) -> List[Block]:
    """
    隣接するブロックを段落として結合する。

    注意: この関数は分類（_classify_blocks）の前に呼ばれるため、
    全ブロックが BlockType.UNKNOWN である。したがって type による判定は使えず、
    フォントサイズ・縦の近さ・横位置の揃いで「同じ段落の続き」かを判定する。

    Args:
        blocks: ブロックリスト
        threshold: 結合する縦距離の閾値（pt）

    Returns:
        結合後のブロックリスト
    """
    if not blocks:
        return []

    merged = []
    current = blocks[0]

    for next_block in blocks[1:]:
        # フォントサイズがほぼ同じ（見出しと本文の誤結合を防ぐ）
        similar_font = abs(current.style.font_size - next_block.style.font_size) < MERGE_FONT_TOLERANCE
        # 縦方向に近い（次の行がすぐ下にある）
        vertically_close = abs(current.bbox.y1 - next_block.bbox.y0) < threshold
        # 横位置が近い（同じカラム内・同じ字下げ）
        horizontally_aligned = abs(current.bbox.x0 - next_block.bbox.x0) < MERGE_HORIZONTAL_TOLERANCE

        if similar_font and vertically_close and horizontally_aligned:
            # 行末ハイフンは連結、それ以外はスペースで繋ぐ
            if current.content.endswith("-"):
                current.content = current.content[:-1] + next_block.content
            else:
                current.content += " " + next_block.content
            # バウンディングボックスを拡張
            current.bbox = BoundingBox(
                x0=min(current.bbox.x0, next_block.bbox.x0),
                y0=current.bbox.y0,
                x1=max(current.bbox.x1, next_block.bbox.x1),
                y1=next_block.bbox.y1
            )
        else:
            merged.append(current)
            current = next_block

    merged.append(current)
    return merged


def calculate_reading_order(blocks: List[Block]) -> List[Block]:
    """
    ブロックを読み順でソート（2段組み対応）

    アルゴリズム:
    1. ページ幅に対してブロックのX座標分布を見て段数を推定
    2. 1段組みなら (y0, x0) でソート
    3. 2段組みなら「左段を上から下→右段を上から下」の順でソート
    """
    if not blocks:
        return blocks

    # ページ内のX座標の中央値から段境界を推定
    x0_values = sorted(b.bbox.x0 for b in blocks)
    x1_values = sorted(b.bbox.x1 for b in blocks)
    page_x_min = x0_values[0]
    page_x_max = x1_values[-1]
    page_width = page_x_max - page_x_min

    # X座標のギャップで段組みを検出
    # 2段組みの場合、ブロックの中心X座標がページ左半分と右半分に集中する
    centers = sorted(b.bbox.x0 + (b.bbox.x1 - b.bbox.x0) / 2 for b in blocks)
    col_boundary = _detect_column_boundary(centers, page_x_min, page_x_max)

    if col_boundary is None:
        # 1段組み: (y0, x0) でソート
        return sorted(blocks, key=lambda b: (b.bbox.y0, b.bbox.x0))
    else:
        # 2段組み: 左段を上から下 → 右段を上から下
        left  = [b for b in blocks if b.bbox.x0 + (b.bbox.x1 - b.bbox.x0) / 2 < col_boundary]
        right = [b for b in blocks if b.bbox.x0 + (b.bbox.x1 - b.bbox.x0) / 2 >= col_boundary]
        left_sorted  = sorted(left,  key=lambda b: b.bbox.y0)
        right_sorted = sorted(right, key=lambda b: b.bbox.y0)
        return left_sorted + right_sorted


def _detect_column_boundary(centers: List[float], x_min: float, x_max: float) -> float:
    """
    中心X座標の分布からカラム境界を検出。
    2段組みでない場合は None を返す。

    2段組みと判定する条件（すべて満たす）:
    - 中央帯（35%〜65%）にギャップがある（最小binが全体平均の30%以下）
    - 左帯・右帯の両方に有意な集中がある（各20%以上）

    左右両帯の条件がないと、中央に集中する1段組みを誤判定してしまう。
    """
    if not centers or len(centers) < 4:
        return None

    page_width = x_max - x_min
    if page_width <= 0:
        return None

    # ページを20分割してヒストグラムを作成
    bins = 20
    bin_width = page_width / bins
    histogram = [0] * bins

    for c in centers:
        idx = min(int((c - x_min) / bin_width), bins - 1)
        histogram[idx] = histogram[idx] + 1

    mid_start = int(bins * 0.35)
    mid_end   = int(bins * 0.65)
    mid_bins   = histogram[mid_start:mid_end]
    left_bins  = histogram[:mid_start]
    right_bins = histogram[mid_end:]

    total = sum(histogram)
    total_avg = total / bins
    mid_min   = min(mid_bins) if mid_bins else total_avg
    left_sum  = sum(left_bins)
    right_sum = sum(right_bins)

    # 中央ギャップ AND 左帯・右帯の両方に20%以上の集中
    if (total_avg > 0
            and mid_min < total_avg * 0.3
            and left_sum  > total * 0.2
            and right_sum > total * 0.2):
        # ギャップの中心をカラム境界とする
        gap_idx = mid_start + mid_bins.index(min(mid_bins))
        boundary = x_min + (gap_idx + 0.5) * bin_width
        return boundary

    return None

