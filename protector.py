"""
Figure Extractor
PDFから図（画像）を抽出
"""
import fitz  # PyMuPDF
import base64
from io import BytesIO
from pathlib import Path
from typing import List, Tuple


class FigureExtractor:
    """
    PDFから図を抽出
    
    画像をBase64エンコードしてHTMLに埋め込む
    """
    
    def __init__(self):
        self.extracted_images = []
    
    def extract_images_from_pdf(self, pdf_path: str) -> List[Tuple[int, bytes, str]]:
        """
        PDFから全ての画像を抽出
        
        Args:
            pdf_path: PDFファイルパス
            
        Returns:
            List of (page_number, image_bytes, format)
        """
        images = []
        doc = fitz.open(pdf_path)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                
                try:
                    # 画像データを抽出
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    images.append((page_num + 1, image_bytes, image_ext))
                    
                except Exception as e:
                    print(f"⚠️  ページ {page_num + 1} の画像 {img_index} の抽出に失敗: {e}")
        
        doc.close()
        self.extracted_images = images
        
        return images
    
    def image_to_base64(self, image_bytes: bytes, format: str = "png") -> str:
        """
        画像をBase64エンコード
        
        Args:
            image_bytes: 画像データ
            format: 画像フォーマット (png, jpeg, etc.)
            
        Returns:
            data URI
        """
        b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # MIMEタイプ
        mime_types = {
            "png": "image/png",
            "jpeg": "image/jpeg",
            "jpg": "image/jpeg",
            "gif": "image/gif",
            "bmp": "image/bmp",
            "webp": "image/webp"
        }
        
        mime = mime_types.get(format.lower(), "image/png")
        
        return f"data:{mime};base64,{b64}"
    
    def save_images_to_folder(self, pdf_path: str, output_folder: str):
        """
        画像をフォルダに保存
        
        Args:
            pdf_path: PDFファイルパス
            output_folder: 出力フォルダ
        """
        output_path = Path(output_folder)
        output_path.mkdir(parents=True, exist_ok=True)
        
        images = self.extract_images_from_pdf(pdf_path)
        
        for idx, (page_num, image_bytes, ext) in enumerate(images):
            filename = f"page{page_num:03d}_img{idx:03d}.{ext}"
            filepath = output_path / filename
            
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            
            print(f"保存: {filepath}")
        
        print(f"\n✅ {len(images)}個の画像を保存しました: {output_folder}")


def main():
    """テスト"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python figure_extractor.py <pdf_file> [output_folder]")
        return
    
    pdf_path = sys.argv[1]
    output_folder = sys.argv[2] if len(sys.argv) > 2 else "extracted_images"
    
    extractor = FigureExtractor()
    extractor.save_images_to_folder(pdf_path, output_folder)


if __name__ == "__main__":
    main()
