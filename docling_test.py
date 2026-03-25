"""
Copyright (c) 2025 IBM Corp.

pip install docling
"""

from docling.document_converter import DocumentConverter
import os 

file_path = 'C:/Users/CiRou/.00_Dev/OCR_20251230/src/document/test02.pdf'  # document per local path or URL
converter = DocumentConverter()
result = converter.convert(file_path)
print(result.document.export_to_markdown())  # output: "## Docling Technical Report[...]"