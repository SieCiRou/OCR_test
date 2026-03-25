"""
Docstring for OCR_main_v3_re
使用 re 提取關鍵字詞區塊
加入讓使用者自行新增/修改提取欄位的功能
進階手寫 OCR 工具 (支援圖片 & PDF)

pip3 install easyocr opencv-python numpy pillow python-docx pandas pdf2image
"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import easyocr
import cv2
import numpy as np
from PIL import Image, ImageTk
from docx import Document
import pandas as pd
import os
import threading
import re
from pdf2image import convert_from_path

# Poppler 路徑設定
poppler_path = r"C:\Users\CiRou\.00_Dev\OCR_20251230\poppler-25.12.0\Library\bin"

class OCRApp:
    def __init__(self, root):
        self.root = root
        self.root.title("動態關鍵字 OCR 提取工具")
        self.root.geometry("1100x850")

        # 初始化 EasyOCR
        self.reader = easyocr.Reader(['ch_tra', 'en'], gpu=False)

        # --- UI 佈局 ---
        main_frame = tk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 左側控制區
        ctrl_frame = tk.Frame(main_frame, width=300)
        ctrl_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        tk.Label(ctrl_frame, text="1. 設定提取關鍵字", font=("微軟正黑體", 12, "bold")).pack(pady=5)
        
        # 關鍵字輸入區
        kw_input_frame = tk.Frame(ctrl_frame)
        kw_input_frame.pack(fill=tk.X)
        self.kw_entry = tk.Entry(kw_input_frame, font=("微軟正黑體", 10))
        self.kw_entry.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        self.kw_entry.insert(0, "數量")
        
        add_kw_btn = tk.Button(kw_input_frame, text="新增", command=self.add_keyword)
        add_kw_btn.pack(side=tk.RIGHT)

        # 關鍵字清單 (多選)
        tk.Label(ctrl_frame, text="目前搜尋清單 (可多選):", font=("微軟正黑體", 9)).pack(anchor="w", pady=2)
        self.kw_listbox = tk.Listbox(ctrl_frame, selectmode=tk.MULTIPLE, height=10)
        self.kw_listbox.pack(fill=tk.X, pady=5)
        
        # 預設關鍵字
        for default_kw in ["Buyer", "Invoice", "Total", "Ship To", "Bill To", "Date"]:
            self.kw_listbox.insert(tk.END, default_kw)

        remove_kw_btn = tk.Button(ctrl_frame, text="刪除選中關鍵字", command=self.remove_keyword)
        remove_kw_btn.pack(fill=tk.X, pady=2)

        tk.Label(ctrl_frame, text="2. 檔案操作", font=("微軟正黑體", 12, "bold")).pack(pady=10)
        self.select_btn = tk.Button(ctrl_frame, text="選擇檔案 (圖片/PDF)", command=self.select_file)
        self.select_btn.pack(fill=tk.X, pady=2)

        self.process_btn = tk.Button(ctrl_frame, text="開始辨識", bg="#2196F3", fg="white", command=self.start_ocr, state=tk.DISABLED)
        self.process_btn.pack(fill=tk.X, pady=2)

        # 右側顯示區
        display_frame = tk.Frame(main_frame)
        display_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        self.progress = ttk.Progressbar(display_frame, mode="determinate")
        self.progress.pack(fill=tk.X, pady=5)

        self.image_label = tk.Label(display_frame, bg="gray95", height=15)
        self.image_label.pack(fill=tk.X, pady=5)

        # 文字結果
        self.result_text = tk.Text(display_frame, height=9, font=("Consolas", 10))
        self.result_text.pack(fill=tk.BOTH, expand=True, pady=5)

        self.extract_display = tk.Text(display_frame, height=8, bg="#E3F2FD", font=("微軟正黑體", 10))
        self.extract_display.pack(fill=tk.X, pady=5)

        self.save_btn = tk.Button(display_frame, text="儲存結果 (Excel/Docx)", bg="#4E7CA7", fg="white", command=self.save_results, state=tk.DISABLED)
        self.save_btn.pack(pady=5)

        # 資料變數
        self.file_path = None
        self.all_results = []
        self.full_text = ""
        self.extracted_data = {}

    # --- 功能函數 ---

    def add_keyword(self):
        new_kw = self.kw_entry.get().strip()
        if new_kw:
            self.kw_listbox.insert(tk.END, new_kw)
            self.kw_entry.delete(0, tk.END)

    def remove_keyword(self):
        selected_indices = self.kw_listbox.curselection()
        for index in reversed(selected_indices):
            self.kw_listbox.delete(index)

    def select_file(self):
        path = filedialog.askopenfilename(filetypes=[("支援檔案", "*.jpg *.png *.pdf")])
        if path:
            self.file_path = path
            self.process_btn.config(state=tk.NORMAL)
            self.preview_file(path)

    def preview_file(self, path):
        try:
            if path.lower().endswith('.pdf'):
                img = convert_from_path(path, dpi=100, first_page=1, last_page=1, poppler_path=poppler_path)[0]
            else:
                img = Image.open(path)
            img.thumbnail((400, 200))
            img_tk = ImageTk.PhotoImage(img)
            self.image_label.config(image=img_tk)
            self.image_label.image = img_tk
        except:
            self.image_label.config(text="預覽不可用")

    def start_ocr(self):
        selected_kws = [self.kw_listbox.get(i) for i in self.kw_listbox.curselection()]
        if not selected_kws:
            messagebox.showwarning("提示", "請至少在清單中選擇一個關鍵字進行搜尋")
            return
        
        self.process_btn.config(state=tk.DISABLED)
        threading.Thread(target=self.run_ocr_logic, args=(selected_kws,), daemon=True).start()

    def run_ocr_logic(self, target_keywords):
        try:
            if self.file_path.lower().endswith('.pdf'):
                images = convert_from_path(self.file_path, dpi=300, poppler_path=poppler_path)
            else:
                images = [Image.open(self.file_path)]

            accumulated_text = ""
            self.all_results = []
            
            for i, img_pil in enumerate(images):
                # 影像預處理
                img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
                gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                processed = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
                
                # OCR 辨識
                raw = self.reader.readtext(processed, paragraph=True)
                page_text = "\n".join([item[1] for item in raw])
                accumulated_text += f"\n[Page {i+1}]\n{page_text}\n"
                
                self.all_results.append({"page": i+1, "text": page_text, "details": raw})
                self.root.after(0, lambda v=(i+1)/len(images)*100: self.progress.config(value=v))

            self.full_text = accumulated_text
            
            # --- 動態正則提取 ---
            self.extracted_data = {}
            for kw in target_keywords:
                # 建立正則：關鍵字 + 冒號(可選) + 內容
                pattern = rf'{re.escape(kw)}[:：\s]*(.*)'
                matches = re.findall(pattern, self.full_text, re.IGNORECASE)
                self.extracted_data[kw] = "; ".join([m.strip() for m in matches]) if matches else "未找到"

            self.root.after(0, self.update_ui_after_ocr)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("錯誤", str(e)))
        finally:
            self.root.after(0, lambda: self.process_btn.config(state=tk.NORMAL))

    def update_ui_after_ocr(self):
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, self.full_text)
        
        self.extract_display.delete(1.0, tk.END)
        self.extract_display.insert(tk.END, "--- 根據選定關鍵字提取結果 ---\n")
        for k, v in self.extracted_data.items():
            self.extract_display.insert(tk.END, f"【{k}】: {v}\n")
        
        self.save_btn.config(state=tk.NORMAL)

    def save_results(self):
        save_path = filedialog.askdirectory()
        if not save_path: return
        
        base = os.path.splitext(os.path.basename(self.file_path))[0]
        
        # Excel 儲存
        with pd.ExcelWriter(os.path.join(save_path, f"{base}_result.xlsx")) as writer:
            pd.DataFrame(list(self.extracted_data.items()), columns=["關鍵字", "內容"]).to_excel(writer, sheet_name="提取結果", index=False)
            pd.DataFrame([{"頁面": r["page"], "全文": r["text"]} for r in self.all_results]).to_excel(writer, sheet_name="全文備份", index=False)
        
        messagebox.showinfo("成功", "資料已匯出至 Excel")

if __name__ == "__main__":
    root = tk.Tk()
    app = OCRApp(root)
    root.mainloop()