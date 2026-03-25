import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
from PIL import Image, ImageTk
import pandas as pd
from pathlib import Path

class OCRCurator:
    def __init__(self, root):
        self.root = root
        self.root.title("OCR 表格校正工具")
        self.root.geometry("1200x800")

        self.db_path = None
        self.current_data = []
        self.current_index = 0

        self.setup_ui()

    def setup_ui(self):
        # --- 上方控制列 ---
        top_frame = ttk.Frame(self.root)
        top_frame.pack(side="top", fill="x", padx=10, pady=5)
        
        # 新增「開啟資料庫」按鈕
        ttk.Button(top_frame, text="📂 開啟資料庫 (.db)", command=self.select_db).pack(side="left", padx=5)
        self.status_label = ttk.Label(top_frame, text="請先開啟 database 資料夾下的 .db 檔案")
        self.status_label.pack(side="left", padx=20)

        # --- 中間主區域 (左右分割) ---
        main_paned = ttk.PanedWindow(self.root, orient="horizontal")
        main_paned.pack(fill="both", expand=True, padx=10, pady=10)

        # 左側：圖片顯示 (加個捲軸防止大圖撐爆)
        img_container = ttk.Frame(main_paned)
        self.img_label = ttk.Label(img_container)
        self.img_label.pack()
        main_paned.add(img_container, weight=1)

        # 右側：文字編輯區
        edit_frame = ttk.Frame(main_paned)
        main_paned.add(edit_frame, weight=1)
        
        ttk.Label(edit_frame, text="編輯 CSV 內容: (修改後請點選儲存)").pack(anchor="w")
        self.text_editor = tk.Text(edit_frame, undo=True, wrap="none", font=("Consolas", 10))
        self.text_editor.pack(fill="both", expand=True)

        # --- 下方導覽列 ---
        nav_frame = ttk.Frame(self.root)
        nav_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        ttk.Button(nav_frame, text="⬅ 上一筆", command=self.prev_item).pack(side="left", padx=20)
        ttk.Button(nav_frame, text="下一筆 ➡", command=self.next_item).pack(side="left")
        ttk.Button(nav_frame, text="💾 儲存目前修改", command=self.save_correction).pack(side="right", padx=20)

    def select_db(self):
        file_path = filedialog.askopenfilename(
            initialdir="./database",
            title="選擇資料庫檔案",
            filetypes=(("SQLite files", "*.db"), ("all files", "*.*"))
        )
        if file_path:
            self.db_path = Path(file_path)
            self.load_data_from_db()

    def load_data_from_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            # 先檢查 table 是否存在
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='page_tables'")
            if not cursor.fetchone():
                messagebox.showerror("錯誤", "此資料庫內沒有 page_tables 表格！\n請先執行 OCR 主程式產生資料。")
                return

            query = "SELECT rowid, page, table_index, img_path, csv_content FROM page_tables"
            self.current_data = pd.read_sql_query(query, conn).to_dict('records')
            conn.close()

            if self.current_data:
                self.current_index = 0
                self.display_current()
            else:
                messagebox.showinfo("提示", "資料庫是空的，沒有可校正的資料。")
        except Exception as e:
            messagebox.showerror("資料庫錯誤", f"無法讀取資料庫：{e}")

    def display_current(self):
        if not self.current_data: return
        item = self.current_data[self.current_index]
        self.status_label.config(text=f"檔案: {self.db_path.name} | 第 {self.current_index + 1} / {len(self.current_data)} 筆")

        # 顯示圖片
        try:
            # 修正路徑問題：如果主程式用相對路徑存，這裡要確保路徑正確
            img_p = Path(item['img_path'])
            if not img_p.exists():
                # 嘗試在當前目錄下找
                img_p = Path(__file__).parent / item['img_path']

            img = Image.open(img_p)
            img.thumbnail((500, 600))
            self.photo = ImageTk.PhotoImage(img)
            self.img_label.config(image=self.photo)
        except Exception as e:
            self.img_label.config(image='', text=f"找不到圖片: {item['img_path']}")

        self.text_editor.delete("1.0", tk.END)
        self.text_editor.insert("1.0", item['csv_content'])

    def save_correction(self):
        if not self.db_path: return
        new_content = self.text_editor.get("1.0", tk.END).strip()
        rowid = self.current_data[self.current_index]['rowid']
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("UPDATE page_tables SET csv_content = ? WHERE rowid = ?", (new_content, rowid))
            conn.commit()
            conn.close()
            self.current_data[self.current_index]['csv_content'] = new_content
            messagebox.showinfo("成功", "校正內容已儲存！")
        except Exception as e:
            messagebox.showerror("儲存失敗", str(e))

    def next_item(self):
        if self.current_index < len(self.current_data) - 1:
            self.current_index += 1
            self.display_current()

    def prev_item(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.display_current()

if __name__ == "__main__":
    root = tk.Tk()
    app = OCRCurator(root)
    root.mainloop()