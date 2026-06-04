"""
Layout Renderer
元のPDFレイアウトを保持したHTMLを生成
"""
from typing import Optional
from pathlib import Path

from ..parser.pdf_document import (
    PDFDocument, Page, Block, Figure, Table,
    BlockType
)


class LayoutHTMLRenderer:
    """
    レイアウト保持HTMLレンダラー
    
    PDFの座標をそのまま使用してHTMLを生成。
    元のPDFと同じレイアウトで表示される。
    """
    
    def __init__(self, scale: float = 1.0, pdf_path: str = None):
        """
        Args:
            scale: 表示スケール（1.0 = 原寸、0.8 = 80%表示）
            pdf_path: 元のPDFパス（図表抽出用、Noneならプレースホルダのみ）
        """
        self.scale = scale
        self.pdf_path = pdf_path
        self.figure_data = {}  # 抽出済み図表のキャッシュ
    
    def render(self, doc: PDFDocument, output_path: Optional[str] = None) -> str:
        """
        HTMLを生成
        
        Args:
            doc: PDFDocument
            output_path: 保存先（Noneなら返すのみ）
        
        Returns:
            HTML文字列
        """
        # 図表を自動抽出
        if self.pdf_path:
            self._extract_all_figures(doc)
        
        html = self._generate_html(doc)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
        
        return html
    
    def _extract_all_figures(self, doc: PDFDocument):
        """全ての図表をPDFから抽出"""
        import fitz
        import base64

        print(f"📷 図表をPDFから抽出中...")

        pdf_doc = fitz.open(self.pdf_path)
        total_figures = 0

        # 解像度定数（150 DPI）
        DPI = 150
        zoom = DPI / 72.0
        mat = fitz.Matrix(zoom, zoom)

        try:
            for page in doc.pages:
                page_num = page.number - 1
                pdf_page = pdf_doc[page_num]

                for figure in page.figures:
                    rect = fitz.Rect(figure.bbox.x0, figure.bbox.y0,
                                     figure.bbox.x1, figure.bbox.y1)
                    pix = pdf_page.get_pixmap(matrix=mat, clip=rect)
                    b64 = base64.b64encode(pix.tobytes("png")).decode('utf-8')
                    self.figure_data[figure.id] = f"data:image/png;base64,{b64}"
                    total_figures += 1

                for table in page.tables:
                    rect = fitz.Rect(table.bbox.x0, table.bbox.y0,
                                     table.bbox.x1, table.bbox.y1)
                    pix = pdf_page.get_pixmap(matrix=mat, clip=rect)
                    b64 = base64.b64encode(pix.tobytes("png")).decode('utf-8')
                    self.figure_data[table.id] = f"data:image/png;base64,{b64}"
                    total_figures += 1
        finally:
            pdf_doc.close()

        print(f"   ✅ {total_figures}個の図表を抽出完了")
    
    
    def _generate_html(self, doc: PDFDocument) -> str:
        """HTML生成"""
        
        html_parts = []
        
        # HTML ヘッダー
        html_parts.append(self._generate_head(doc))
        
        # ボディ開始
        html_parts.append('<body>')
        
        # タイトルバー
        html_parts.append(self._generate_titlebar(doc))
        
        # コンテナ
        html_parts.append('<div class="container">')
        
        # ページごとに生成
        for page in doc.pages:
            html_parts.append(self._generate_page(page, doc))
        
        html_parts.append('</div>')  # container
        
        # フッター
        html_parts.append(self._generate_footer(doc))
        
        html_parts.append('</body>')
        html_parts.append('</html>')
        
        return '\n'.join(html_parts)
    
    def _generate_head(self, doc: PDFDocument) -> str:
        """HTMLヘッダー生成"""
        title = self._escape_html(doc.metadata.get("title", "Translated Paper"))
        
        return f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 翻訳版</title>
    
    <!-- MathJax -->
    
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    
    <style>
        {self._generate_css(doc)}
    </style>
</head>"""
    
    def _generate_css(self, doc: PDFDocument) -> str:
        """CSS生成"""
        
        # 最初のページのサイズを基準に
        if doc.pages:
            page_width = doc.pages[0].width * self.scale
            page_height = doc.pages[0].height * self.scale
        else:
            page_width = 595 * self.scale  # A4幅
            page_height = 842 * self.scale  # A4高さ
        
        return f"""
        /* Reset */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Noto Sans JP', 'Hiragino Kaku Gothic Pro', 'Yu Gothic', 'Meiryo', sans-serif;
            background: #f5f5f5;
            padding: 20px;
            line-height: 1.6;
        }}
        
        /* タイトルバー */
        .titlebar {{
            background: white;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-radius: 8px;
        }}
        
        .titlebar h1 {{
            font-size: 24px;
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        
        .titlebar .meta {{
            color: #7f8c8d;
            font-size: 14px;
        }}
        
        /* コンテナ */
        .container {{
            max-width: {page_width + 40}px;
            margin: 0 auto;
        }}
        
        /* ページ */
        .page {{
            width: {page_width}px;
            min-height: {page_height}px;
            background: white;
            position: relative;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 20px;
        }}
        
        .page-number {{
            position: absolute;
            bottom: 10px;
            right: 10px;
            font-size: 12px;
            color: #95a5a6;
        }}
        
        /* ブロック - 重なり防止 */
        .block {{
            position: relative;
            margin-bottom: 10px;
            word-wrap: break-word;
            overflow-wrap: break-word;
            hyphens: auto;
        }}
        
        /* タイトル */
        .block.title {{
            font-weight: bold;
            color: #2c3e50;
            font-size: 1.5em;
            margin-bottom: 15px;
            line-height: 1.4;
        }}
        
        /* Abstract */
        .block.abstract {{
            color: #34495e;
            background: #f8f9fa;
            padding: 15px;
            border-left: 4px solid #3498db;
            margin-bottom: 20px;
        }}
        
        /* 見出し */
        .block.heading1,
        .block.heading2,
        .block.heading3 {{
            font-weight: bold;
            color: #2c3e50;
            margin-top: 20px;
            margin-bottom: 10px;
        }}
        
        .block.heading1 {{
            font-size: 1.3em;
            border-bottom: 2px solid #3498db;
            padding-bottom: 5px;
        }}
        
        .block.heading2 {{
            font-size: 1.2em;
        }}
        
        .block.heading3 {{
            font-size: 1.1em;
        }}
        
        /* 段落 */
        .block.paragraph {{
            text-align: justify;
            color: #2c3e50;
            line-height: 1.8;
            margin-bottom: 12px;
        }}
        
        /* 数式 */
        .block.equation {{
            text-align: center;
            font-family: 'Times New Roman', serif;
            color: #2c3e50;
            margin: 15px 0;
            padding: 10px 0;
        }}
        
        /* キャプション */
        .block.caption {{
            font-size: 0.9em;
            font-style: italic;
            color: #555;
            text-align: center;
            margin-top: 5px;
            margin-bottom: 15px;
        }}
        
        /* コード */
        .block.code {{
            font-family: 'Courier New', monospace;
            background: #f8f9fa;
            padding: 10px;
            border-left: 3px solid #3498db;
            overflow-x: auto;
            margin: 10px 0;
        }}
        
        /* 参考文献 */
        .block.reference {{
            font-size: 0.85em;
            color: #555;
            margin-bottom: 5px;
        }}
        
        /* 図 */
        .figure-container {{
            margin: 30px auto;
            padding: 20px;
            background: #fafafa;
            border: 2px solid #ddd;
            border-radius: 8px;
            max-width: 90%;
            text-align: center;
            page-break-inside: avoid;
        }}
        
        .figure-placeholder {{
            margin-bottom: 15px;
            min-height: 200px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #f0f0f0;
            border-radius: 4px;
        }}
        
        .figure-placeholder svg {{
            width: 100%;
            max-width: 600px;
            height: auto;
        }}
        
        .figure-caption {{
            text-align: center;
            font-size: 0.9em;
            font-style: italic;
            color: #555;
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #ddd;
        }}
        
        /* 表 */
        .table-container {{
            margin: 30px auto;
            padding: 20px;
            overflow-x: auto;
            max-width: 95%;
            background: white;
            border: 2px solid #ddd;
            border-radius: 8px;
            page-break-inside: avoid;
        }}
        
        .paper-table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            font-size: 0.9em;
        }}
        
        .paper-table td,
        .paper-table th {{
            border: 1px solid #ddd;
            padding: 10px 15px;
            text-align: left;
            vertical-align: top;
        }}
        
        .paper-table th {{
            background: #f5f5f5;
            font-weight: bold;
        }}
        
        .paper-table tr:nth-child(even) {{
            background: #fafafa;
        }}
        
        .paper-table tr:hover {{
            background: #f0f0f0;
        }}
        
        .table-caption {{
            text-align: center;
            font-size: 0.9em;
            font-style: italic;
            color: #555;
            margin-top: 15px;
            padding-top: 10px;
            border-top: 1px solid #ddd;
        }}
        
        /* 図表のラベル */
        .figure-label,
        .table-label {{
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        
        /* ヘッダー・フッター */
        .block.header,
        .block.footer {{
            font-size: 0.8em;
            color: #95a5a6;
        }}
        
        /* フッター */
        .site-footer {{
            background: white;
            padding: 20px;
            margin-top: 20px;
            box-shadow: 0 -2px 4px rgba(0,0,0,0.1);
            border-radius: 8px;
            text-align: center;
            color: #7f8c8d;
            font-size: 14px;
        }}
        
        /* レスポンシブ */
        @media (max-width: {page_width + 60}px) {{
            .container {{
                padding: 10px;
            }}
            
            .page {{
                width: 100%;
                min-height: auto;
                padding: 15px;
            }}
        }}
        
        /* 印刷 */
        @media print {{
            body {{
                background: white;
            }}
            
            .titlebar,
            .site-footer {{
                display: none;
            }}
            
            .page {{
                box-shadow: none;
                margin-bottom: 0;
                page-break-after: always;
            }}
            
            .block {{
                page-break-inside: avoid;
            }}
        }}
        """
    
    def _generate_titlebar(self, doc: PDFDocument) -> str:
        """タイトルバー生成"""
        title = self._escape_html(doc.metadata.get("title", "Untitled"))
        authors = self._escape_html(", ".join(doc.metadata.get("authors", [])))
        stats = doc.get_statistics()
        
        return f"""
        <div class="titlebar">
            <h1>{title}</h1>
            <div class="meta">
                {f'著者: {authors}<br>' if authors else ''}
                ページ数: {stats['page_count']} | 
                翻訳ブロック: {stats['translatable_blocks']} | 
                総文字数: {stats['total_characters']:,}
            </div>
        </div>
        """
    
    def _generate_page(self, page: Page, doc: PDFDocument) -> str:
        """ページHTML生成"""
        parts = []
        parts.append(f'<div class="page" data-page="{page.number}">')
        
        # ブロックと図表を統合してソート（Y座標順）
        all_items = []
        
        # テキストブロック
        for block in page.blocks:
            all_items.append({
                'type': 'block',
                'y': block.bbox.y0,
                'content': block,
                'height': block.bbox.height
            })
        
        # 図
        for figure in page.figures:
            all_items.append({
                'type': 'figure',
                'y': figure.bbox.y0,
                'content': figure,
                'height': figure.bbox.height
            })
        
        # 表
        for table in page.tables:
            all_items.append({
                'type': 'table',
                'y': table.bbox.y0,
                'content': table,
                'height': table.bbox.height
            })
        
        # Y座標でソート（上から下へ）
        all_items.sort(key=lambda x: x['y'])
        
        # 順番に描画
        for item in all_items:
            if item['type'] == 'block':
                block = item['content']
                # figure/table のキャプションとして関連付け済みなら二重描画を防ぐ
                if block.metadata.get("is_figure_caption"):
                    continue
                parts.append(self._generate_block(block, page))
            elif item['type'] == 'figure':
                parts.append(self._generate_figure(item['content'], page))
            elif item['type'] == 'table':
                parts.append(self._generate_table(item['content'], page))
        
        # ページ番号
        parts.append(f'<div class="page-number">Page {page.number}</div>')
        
        parts.append('</div>')
        
        return '\n'.join(parts)
    
    def _generate_block(self, block: Block, page: Page) -> str:
        """ブロックHTML生成"""
        # フォントサイズ
        font_size = block.style.font_size * self.scale
        font_weight = "bold" if block.style.is_bold else "normal"
        font_style = "italic" if block.style.is_italic else "normal"
        
        # 相対配置スタイル（重なり防止）
        style = f"""
            font-size: {font_size}px;
            font-weight: {font_weight};
            font-style: {font_style};
        """.strip()
        
        # コンテンツ
        content = block.content
        
        # 数式の場合はMathJax形式に
        if block.type == BlockType.EQUATION:
            if not content.startswith('$'):
                content = f'$${content}$$'
        
        # HTMLエスケープ（数式以外）
        if block.type not in [BlockType.EQUATION]:
            content = self._escape_html(content)
        
        block_class = block.type.value
        
        return f'<div class="block {block_class}" style="{style}">{content}</div>'
    
    def _generate_figure(self, figure: Figure, page: Page) -> str:
        """図HTML生成"""
        caption_html = ""
        if figure.caption:
            caption_html = f'<div class="figure-caption">{self._escape_html(figure.caption.content)}</div>'
        
        # 図のラベル
        label_html = f'<div class="figure-label">Figure {figure.id}</div>'
        
        # 実際の画像データがあれば使用
        if figure.id in self.figure_data:
            image_html = f'''
            <div class="figure-image">
                <img src="{self.figure_data[figure.id]}" 
                     alt="Figure {figure.id}" 
                     style="max-width: 100%; height: auto; border: 1px solid #ddd;">
            </div>
            '''
        else:
            # プレースホルダ
            image_html = f'''
            <div class="figure-placeholder">
                <svg viewBox="0 0 600 300" xmlns="http://www.w3.org/2000/svg">
                    <rect width="100%" height="100%" fill="#f0f0f0" rx="4"/>
                    <text x="50%" y="50%" text-anchor="middle" dominant-baseline="middle" 
                          fill="#999" font-size="18" font-family="Arial, sans-serif">
                        図 {figure.id}
                    </text>
                    <text x="50%" y="60%" text-anchor="middle" dominant-baseline="middle" 
                          fill="#bbb" font-size="14" font-family="Arial, sans-serif">
                        (PDFパスを指定すると自動抽出されます)
                    </text>
                </svg>
            </div>
            '''
        
        return f'''
        <div class="figure-container">
            {label_html}
            {image_html}
            {caption_html}
        </div>
        '''
    
    def _generate_table(self, table: Table, page: Page) -> str:
        """表HTML生成"""
        parts = []
        parts.append('<div class="table-container">')
        
        # 表のラベル
        parts.append(f'<div class="table-label">Table {table.id}</div>')
        
        # 実際の画像データがあれば使用（表は画像として表示）
        if table.id in self.figure_data:
            parts.append(f'''
            <div class="table-image">
                <img src="{self.figure_data[table.id]}" 
                     alt="Table {table.id}" 
                     style="max-width: 100%; height: auto; border: 1px solid #ddd;">
            </div>
            ''')
        elif table.cells:
            # フォールバック: HTMLテーブル
            parts.append('<table class="paper-table">')
            
            for row_idx, row in enumerate(table.cells):
                tag = 'th' if row_idx == 0 else 'td'
                parts.append('<tr>')
                for cell in row:
                    cell_content = self._escape_html(cell.content) if cell.content else "&nbsp;"
                    parts.append(f'<{tag}>{cell_content}</{tag}>')
                parts.append('</tr>')
            
            parts.append('</table>')
        
        # キャプション
        if table.caption:
            caption = self._escape_html(table.caption.content)
            parts.append(f'<div class="table-caption">{caption}</div>')
        
        parts.append('</div>')
        
        return '\n'.join(parts)
    
    def _generate_footer(self, doc: PDFDocument) -> str:
        """フッター生成"""
        return """
        <div class="site-footer">
            学術論文翻訳システム v2.0 で翻訳
        </div>
        """
    
    def _escape_html(self, text: str) -> str:
        """HTMLエスケープ"""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))


def main():
    """テスト"""
    import sys
    from ..parser.pdf_document import PDFDocument
    
    if len(sys.argv) < 2:
        print("Usage: python layout_renderer.py <structure.json>")
        return
    
    json_path = sys.argv[1]
    
    # JSONから読み込み
    doc = PDFDocument.from_json(json_path)
    
    # HTML生成
    renderer = LayoutHTMLRenderer(scale=0.8)
    
    output_path = Path(json_path).stem + "_layout.html"
    renderer.render(doc, output_path)
    
    print(f"Generated: {output_path}")


if __name__ == "__main__":
    main()
