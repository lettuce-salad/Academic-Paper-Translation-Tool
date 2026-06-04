"""
Dual Column Renderer
原文と翻訳を並列表示するHTMLレンダラー
"""
from typing import Optional
from pathlib import Path

from ..parser.pdf_document import PDFDocument, BlockType


class DualColumnRenderer:
    """
    2カラム表示レンダラー
    
    左: 原文（英語）
    右: 翻訳（日本語）
    """
    
    def __init__(self):
        pass
    
    def render(self, doc: PDFDocument, output_path: Optional[str] = None) -> str:
        """
        2カラムHTMLを生成
        
        Args:
            doc: PDFDocument（翻訳済み）
            output_path: 保存先
            
        Returns:
            HTML文字列
        """
        html = self._generate_html(doc)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
        
        return html
    
    def _generate_html(self, doc: PDFDocument) -> str:
        """HTML生成"""
        parts = []
        
        # ヘッダー
        parts.append(self._generate_head(doc))
        parts.append('<body>')
        
        # タイトルバー
        parts.append(self._generate_titlebar(doc))
        
        # コンテナ
        parts.append('<div class="container">')
        parts.append('<div class="dual-columns">')
        
        # 左カラム: 原文
        parts.append('<div class="column original">')
        parts.append('<h2>Original (English)</h2>')
        parts.append(self._generate_content(doc, original=True))
        parts.append('</div>')
        
        # 右カラム: 翻訳
        parts.append('<div class="column translated">')
        parts.append('<h2>Translation (Japanese)</h2>')
        parts.append(self._generate_content(doc, original=False))
        parts.append('</div>')
        
        parts.append('</div>')  # dual-columns
        parts.append('</div>')  # container
        
        # フッター
        parts.append(self._generate_footer())
        
        parts.append('</body>')
        parts.append('</html>')
        
        return '\n'.join(parts)
    
    def _generate_head(self, doc: PDFDocument) -> str:
        """HTMLヘッダー"""
        title = self._escape_html(doc.metadata.get("title", "Translated Paper"))
        
        return f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 原文・翻訳対照</title>
    
    <!-- MathJax -->
    
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    
    <style>
        {self._generate_css()}
    </style>
</head>"""
    
    def _generate_css(self) -> str:
        """CSS生成"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Noto Sans JP', 'Hiragino Kaku Gothic Pro', 'Yu Gothic', sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }
        
        .titlebar {
            background: white;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-radius: 8px;
            text-align: center;
        }
        
        .titlebar h1 {
            font-size: 24px;
            color: #2c3e50;
            margin-bottom: 10px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .dual-columns {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            align-items: start;
        }
        
        .column {
            background: white;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-radius: 8px;
            min-height: 500px;
        }
        
        .column h2 {
            font-size: 18px;
            color: #2c3e50;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #3498db;
            position: sticky;
            top: 0;
            background: white;
            z-index: 10;
        }
        
        .column.original {
            border-left: 4px solid #e74c3c;
        }
        
        .column.translated {
            border-left: 4px solid #3498db;
        }
        
        .block {
            margin-bottom: 15px;
            line-height: 1.8;
            scroll-margin-top: 80px;
        }
        
        .block.title {
            font-size: 1.5em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 20px;
        }
        
        .block.abstract {
            background: #f8f9fa;
            padding: 15px;
            border-left: 4px solid #95a5a6;
            margin-bottom: 20px;
        }
        
        .block.heading1 {
            font-size: 1.3em;
            font-weight: bold;
            color: #2c3e50;
            margin-top: 25px;
            margin-bottom: 15px;
            padding-bottom: 5px;
            border-bottom: 2px solid #3498db;
        }
        
        .block.heading2 {
            font-size: 1.2em;
            font-weight: bold;
            color: #2c3e50;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        
        .block.heading3 {
            font-size: 1.1em;
            font-weight: bold;
            color: #34495e;
            margin-top: 15px;
            margin-bottom: 8px;
        }
        
        .block.paragraph {
            text-align: justify;
            color: #2c3e50;
        }
        
        .block.equation {
            text-align: center;
            margin: 20px 0;
            padding: 15px;
            background: #f8f9fa;
        }
        
        .block.caption {
            font-size: 0.9em;
            font-style: italic;
            color: #7f8c8d;
            text-align: center;
            margin: 10px 0;
        }
        
        .block.code {
            font-family: 'Courier New', monospace;
            background: #f8f9fa;
            padding: 10px;
            border-left: 3px solid #3498db;
            overflow-x: auto;
            font-size: 0.9em;
        }
        
        .site-footer {
            background: white;
            padding: 20px;
            margin-top: 20px;
            box-shadow: 0 -2px 4px rgba(0,0,0,0.1);
            border-radius: 8px;
            text-align: center;
            color: #7f8c8d;
        }
        
        /* レスポンシブ */
        @media (max-width: 1200px) {
            .dual-columns {
                grid-template-columns: 1fr;
            }
            
            .column.original {
                order: 1;
            }
            
            .column.translated {
                order: 2;
            }
        }
        
        /* 印刷 */
        @media print {
            .dual-columns {
                grid-template-columns: 1fr 1fr;
                gap: 10px;
            }
            
            .column {
                box-shadow: none;
                padding: 15px;
            }
            
            .titlebar, .site-footer {
                display: none;
            }
        }
        """
    
    def _generate_titlebar(self, doc: PDFDocument) -> str:
        """タイトルバー"""
        title = self._escape_html(doc.metadata.get("title", "Untitled"))
        stats = doc.get_statistics()
        
        return f"""
        <div class="titlebar">
            <h1>{title}</h1>
            <p>原文・翻訳対照表示</p>
        </div>
        """
    
    def _generate_content(self, doc: PDFDocument, original: bool) -> str:
        """コンテンツ生成"""
        parts = []
        
        for page in doc.pages:
            for block in page.blocks:
                # 翻訳対象ブロックのみ
                if block.type in [
                    BlockType.TITLE,
                    BlockType.ABSTRACT,
                    BlockType.HEADING1,
                    BlockType.HEADING2,
                    BlockType.HEADING3,
                    BlockType.PARAGRAPH,
                    BlockType.CAPTION,
                    BlockType.EQUATION,
                ]:
                    # 原文 or 翻訳
                    if original:
                        content = block.original_content or block.content
                    else:
                        content = block.content
                    
                    # 数式の場合
                    if block.type == BlockType.EQUATION:
                        if not content.startswith('$'):
                            content = f'$${content}$$'
                    else:
                        content = self._escape_html(content)
                    
                    parts.append(f'<div class="block {block.type.value}">{content}</div>')
        
        return '\n'.join(parts)
    
    def _generate_footer(self) -> str:
        """フッター"""
        return """
        <div class="site-footer">
            学術論文翻訳システム v2.0 - 原文・翻訳対照表示
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
