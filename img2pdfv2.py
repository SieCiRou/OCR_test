"""sumary_line
use tesseractOCR with  oem: Tesseract and LSTM 
pip install pdfplumber img2table pandas
"""
import os
import sqlite3
import pandas as pd
import pdfplumber
from img2table.document import Image as ImgDoc
from img2table.ocr import TesseractOCR


#--------database-------
def save_to_sqlite(pages_info, db_path="extracted_data.db"):
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS page_text (
            page INTEGER, 
            content TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS page_tables (
            page INTEGER, 
            table_index INTEGER, 
            img_path TEXT, 
            csv_content TEXT
        )
    ''')

    for p in pages_info:
        cursor.execute('INSERT INTO page_text (page, content) VALUES (?, ?)', 
            (p["page"], p["text"]))
    for ti, t_info in enumerate(p["tables"]):
        csv_str = ""
        if t_info.get("tables") and len(t_info["tables"]) > 0:
            df = t_info["tables"][0].df
            csv_str = df.to_csv(index=False)

        cursor.execute('''
            INSERT INTO page_tables (page, table_index, img_path, csv_content) 
            VALUES (?, ?, ?, ?)
        ''', (p["page"], ti, t_info["image_path"], csv_str))

    conn.commit()
    conn.close()
    print(f"data already saved to database: {db_path}")
    



#--------tool-----------
def bbox_intersect(b1,b2):
    x0, y0, x1, y1 = b1
    X0, Y0, X1, Y1 = b2

    return not (x1 <= X0 or X1 <= x0 or y1 <= Y0 or Y1 <= y0)

def group_words_to_lines(words, line_tol=3):
    if not words:
        return ""
    words_sorted = sorted(words, key=lambda w: (round(w["top"]), w["x0"]))
    lines = []
    cur_top = None
    cur_words = []
    for w in words_sorted:
        if cur_top is None:
            cur_top = w["top"]
            cur_words = [w["text"]]
        elif abs(w["top"]-cur_top) <=line_tol:
            cur_words.append(w["text"])
        else:
            lines.append(" ".join(cur_words))
            cur_top = w["top"]
            cur_words = [w["text"]]
    if cur_words:
        lines.append("".join(cur_words))
    return "\n".join(lines)

def extract_text_and_tables(pdf_path, out_dir="output_tables", dpi=150, ocr_lang="eng+chi_tra"):
    os.makedirs(out_dir, exist_ok=True)
    pages_info = []
    ocr = TesseractOCR( lang=ocr_lang, oem = 2, psm=1)

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            words = page.extract_words()
        found_tables = page.find_tables()
        table_bboxes = [t.bbox for t in found_tables]
        if table_bboxes:
            filtered_words = []
            for w in words:
                wb = (w["x0"],w["top"],w["x1"],w["bottom"])
                in_table = any(bbox_intersect(wb, tb)for tb in table_bboxes)

                if not in_table:
                    filtered_words.append(w)
        else:
            filtered_words = words
        
        page_text = group_words_to_lines(filtered_words)
        page_tables_info = []
        if table_bboxes:
            page_image_wrapper = page.to_image(resolution=dpi)
            for ti ,bbox in enumerate(table_bboxes):
                try:
                    cropped_img_wrapper = page_image_wrapper
                    pil_img = cropped_img_wrapper.original
                except Exception:
                    pil_img = page_image_wrapper.original

                img_path = os.path.join(out_dir,f"page_{i}_table_{ti}.png")
                pil_img.save(img_path)
                img_doc = ImgDoc(img_path)
                tables_detected = img_doc.extract_tables(ocr=ocr)

                page_tables_info.append({
                    "bbox": bbox,
                    "image_path": img_path,
                    "tables": tables_detected
                })

            pages_info.append({
                "page": i,
                "text": page_text,
                "tables": page_tables_info
            })

    return pages_info


#----ocr--------
pages = extract_text_and_tables("檔案名稱.pdf", out_dir="out_tables", dpi=300, ocr_lang="eng+chi_tra")