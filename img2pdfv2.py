import os
import sqlite3
import pandas as pd
from pathlib import Path
import pdfplumber
from img2table.document import Image as ImgDoc
from img2table.ocr import TesseractOCR
import pytesseract

# 1. 路徑定義與初始化
tesseract_path = r'C:\Program Files\Tesseract-OCR'
if tesseract_path not in os.environ['PATH']:
    os.environ['PATH'] += f';{tesseract_path}'
pytesseract.pytesseract.tesseract_cmd = r'c:\Users\CiRou\.00_Dev\OCR_test\.venv\Lib\site-packages\tesseract.exe'

BASE_DIR = Path(__file__).parent
PDF_DIR = BASE_DIR / "pdf"
IMG_DIR = BASE_DIR / "img"
EXCEL_DIR = BASE_DIR / "excel"
DB_DIR = BASE_DIR / "database"

# custom_config = r'--oem 3 --psm 1' 

for folder in [IMG_DIR, EXCEL_DIR, DB_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# 2. 輔助工具函數
def bbox_intersect(b1, b2):
    x0, y0, x1, y1 = b1
    X0, Y0, X1, Y1 = b2
    return not (x1 <= X0 or X1 <= x0 or y1 <= Y0 or Y1 <= y0)

def group_words_to_lines(words, line_tol=3):
    if not words: return ""
    words_sorted = sorted(words, key=lambda w: (round(w["top"]), w["x0"]))
    lines, cur_top, cur_words = [], None, []
    for w in words_sorted:
        if cur_top is None:
            cur_top = w["top"]
            cur_words = [w["text"]]
        elif abs(w["top"] - cur_top) <= line_tol:
            cur_words.append(w["text"])
        else:
            lines.append(" ".join(cur_words))
            cur_top, cur_words = w["top"], [w["text"]]
    if cur_words: lines.append(" ".join(cur_words))
    return "\n".join(lines)

# 3. 核心處理邏輯
def run_ocr_process(target_pdf_name):
    pdf_path = PDF_DIR / target_pdf_name
    if not pdf_path.exists():
        print(f"錯誤：找不到檔案 {pdf_path}")
        return

    file_stem = pdf_path.stem
    ocr = TesseractOCR(lang="eng+chi_tra", psm=1)
    pages_info = []

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            print(f"正在處理第 {i} 頁...")
            words = page.extract_words()
            found_tables = page.find_tables()
            table_bboxes = [t.bbox for t in found_tables]
            
            # 過濾文字
            filtered_words = [w for w in words if not any(bbox_intersect((w["x0"], w["top"], w["x1"], w["bottom"]), tb) for tb in table_bboxes)]
            page_text = group_words_to_lines(filtered_words)
            
            # 處理表格
            page_tables_info = []
            for ti, bbox in enumerate(table_bboxes):
                img_name = f"{file_stem}_p{i}_t{ti}.png"
                save_img_path = IMG_DIR / img_name
            
                try:
                    # 先裁頁面，再轉圖片
                    page.crop(bbox).to_image(resolution=300).original.save(save_img_path)
                    img_doc = ImgDoc(str(save_img_path))
                    tables_detected = img_doc.extract_tables(ocr=ocr)
                    page_tables_info.append({
                        "table_index": ti,
                        "image_path": str(save_img_path),
                        "tables": tables_detected # 這是 img2table 的物件列表
                    })

                except Exception as e:
                    print(f"警告：第 {i} 頁表格 {ti} 截圖失敗: {e}")
                    continue

            pages_info.append({
                "page": i,
                "text": page_text, # 表格外的純文字
                "tables": page_tables_info # 表格清單
            })

            # pages_info.append({"page": i, "text": page_text, "tables": page_tables_info})

    # 4. 存入 SQLite 與 Excel
    save_data(pages_info, file_stem)

def save_data(pages_info, file_stem):
    db_path = DB_DIR / f"{Path(__file__).stem}.db"
    excel_path = EXCEL_DIR / f"{file_stem}.xlsx"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # cursor.execute('DROP TABLE IF EXISTS page_text')
    # cursor.execute('DROP TABLE IF EXISTS page_tables')

    cursor.execute('CREATE TABLE IF NOT EXISTS page_text (page INTEGER, content TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS page_tables (page INTEGER, table_index INTEGER, img_path TEXT, csv_content TEXT)')

    with pd.ExcelWriter(excel_path) as writer:
        for p in pages_info:
            cursor.execute('INSERT INTO page_text (page, content) VALUES (?, ?)', (p["page"], p["text"]))
            # cursor.execute('INSERT INTO page_text VALUES (?, ?)', (p["page"], p["text"]))
            
            # 存 SQLite 表格與 Excel
            for ti, t_info in enumerate(p["tables"]):
                csv_data = ""
                if t_info["tables"]:
                    df = t_info["tables"][0].df
                    csv_data = df.to_csv(index=False)
                    # 寫入 Excel 不同分頁
                    sheet_name = f"P{p['page']}_T{ti}"
                    df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
                
                cursor.execute('''
                    INSERT INTO page_tables (page, table_index, img_path, csv_content) 
                    VALUES (?, ?, ?, ?)
                ''', (p["page"], ti, t_info["image_path"], csv_data))

    conn.commit()
    conn.close()
    print(f"--- 處理完成 ---")
    print(f"資料庫: {db_path}\nExcel: {excel_path}\n圖片目錄: {IMG_DIR}")

# 執行程式
if __name__ == "__main__":
    run_ocr_process("DoublePeople_nfore.pdf")