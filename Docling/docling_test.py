"""
Copyright (c) 2025 IBM Corp.

pip install docling
"""

import os
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter, PdfFormatOption


pipeline_options = PdfPipelineOptions()
pipeline_options.do_table_structure = True
pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE

# pipeline_options.generate_page_images = False  # 關閉OCR 圖片可加速
pipeline_options.do_ocr = True # 數字是亂碼，強迫執行 OCR 重新辨識數字

# 1. 設定 PDF 處理選項
pipeline_options = PdfPipelineOptions()
pipeline_options.do_table_structure = True  # 啟用表格結構辨識
pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE  # 使用精確模式

# 2. 設定 PDF 引擎 (預設通常就是 PyPdfium，這裡顯式指定)
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

# 3. 初始化轉換器，將選項帶入
converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(
            pipeline_options=pipeline_options,
            backend=PyPdfiumDocumentBackend
        )
    }
)

file_path = 'C:/Users/CiRou/.00_Dev/OCR_20251230/src/document/test01.pdf'

# 執行轉換
result = converter.convert(file_path)

# 輸出 Markdown
print(result.document.export_to_markdown())
