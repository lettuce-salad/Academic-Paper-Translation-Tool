"""
Automatic Figure Extractor
PDFから図表を自動的に切り抜いてHTMLに埋め込む
"""
import fitz  # PyMuPDF
import base64
from io import BytesIO
from pathlib import Path
from typing import List, Tuple, Dict


class AutoFigureExtractor:
    """
    PDFから図表を自動抽出してHTMLに埋め込む
    """
    
    def __init__(self):
        self.extracted_figures = {}
    
    def extract_figure_from_bbox(self, 
                                  pdf_path: str, 
                                  page_num: int, 
                                  bbox: Tuple[float, float, float, float],
                                  dpi: int = 150) -> str:
        """
        PDFの指定領域を画像として切り抜き
        
        Args:
            pdf_path: PDFファイルパス
            page_num: ページ番号（0始まり）
            bbox: (x0, y0, x1, y1) 座標
            dpi: 解像度
            
        Returns:
            Base64エンコードされた画像データ（data URI）
        """
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        
        # 座標を指定して画像を切り抜き
        # PyMuPDFの座標系に合わせる
        rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
        
        # 拡大率を計算（高解像度で切り抜き）
        zoom = dpi / 72.0  # 72 DPI = 標準
        mat = fitz.Matrix(zoom, zoom)
        
        # 画像として切り抜き
        pix = page.get_pixmap(matrix=mat, clip=rect)
        
        # PNG形式に変換
        img_data = pix.tobytes("png")
        
        # Base64エンコード
        b64_data = base64.b64encode(img_data).decode('utf-8')
        data_uri = f"data:image/png;base64,{b64_data}"
        
        doc.close()
        
        return data_uri
    
    def extract_table_from_bbox(self,
                                 pdf_path: str,
                                 page_num: int,
                                 bbox: Tuple[float, float, float, float],
                                 dpi: int = 150) -> str:
        """
        表を画像として切り抜き
        
        表の中身は英語のままでOK
        """
        # 図と同じ処理
        return self.extract_figure_from_bbox(pdf_path, page_num, bbox, dpi)
    
    def extract_all_figures(self, 
                           pdf_path: str, 
                           pdf_document) -> Dict[str, str]:
        """
        PDFDocument内の全ての図表を抽出
        
        Args:
            pdf_path: PDFファイルパス
            pdf_document: PDFDocumentオブジェクト
            
        Returns:
            {figure_id: data_uri} の辞書
        """
        figures = {}
        
        for page in pdf_document.pages:
            page_num = page.number - 1  # 0始まりに変換
            
            # 図を抽出
            for figure in page.figures:
                bbox = (
                    figure.bbox.x0,
                    figure.bbox.y0,
                    figure.bbox.x1,
                    figure.bbox.y1
                )
                
                print(f"   図を抽出中: {figure.id} (ページ {page.number})")
                
                data_uri = self.extract_figure_from_bbox(
                    pdf_path, 
                    page_num, 
                    bbox,
                    dpi=150
                )
                
                figures[figure.id] = data_uri
            
            # 表を抽出
            for table in page.tables:
                bbox = (
                    table.bbox.x0,
                    table.bbox.y0,
                    table.bbox.x1,
                    table.bbox.y1
                )
                
                print(f"   表を抽出中: {table.id} (ページ {page.number})")
                
                data_uri = self.extract_table_from_bbox(
                    pdf_path,
                    page_num,
                    bbox,
                    dpi=150
                )
                
                figures[table.id] = data_uri
        
        return figures
    
    def save_figure(self, 
                   data_uri: str, 
                   output_path: str):
        """
        Data URIを画像ファイルとして保存
        
        Args:
            data_uri: data:image/png;base64,xxxxx
            output_path: 出力ファイルパス
        """
        # Base64部分を抽出
        base64_data = data_uri.split(',')[1]
        img_data = base64.b64decode(base64_data)
        
        # ファイルに保存
        with open(output_path, 'wb') as f:
            f.write(img_data)


def test_extractor():
    """テスト"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python auto_figure_extractor.py <pdf_file>")
        return
    
    pdf_path = sys.argv[1]
    
    # PDFDocumentを読み込み（簡易版）
    from ..parser.structure_parser import PDFStructureParser
    
    parser = PDFStructureParser()
    doc = parser.parse(pdf_path)
    
    # 図表を抽出
    extractor = AutoFigureExtractor()
    figures = extractor.extract_all_figures(pdf_path, doc)
    
    print(f"\n抽出完了: {len(figures)}個の図表")
    
    # 保存
    output_dir = Path("extracted_figures")
    output_dir.mkdir(exist_ok=True)
    
    for fig_id, data_uri in figures.items():
        output_path = output_dir / f"{fig_id}.png"
        extractor.save_figure(data_uri, str(output_path))
        print(f"保存: {output_path}")


if __name__ == "__main__":
    test_extractor()
