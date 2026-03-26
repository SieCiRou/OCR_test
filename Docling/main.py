import torch
import gc
from PIL import Image

from surya.layout import run_layout_detection
from surya.model.layout.model import load_model as load_layout_model
from surya.model.layout.processor import load_processor as load_layout_processor # 新增這行
from surya.model.detection.model import load_model as load_det_model

from transformers import AutoModel, AutoTokenizer
from pdf2image import convert_from_path
import requests

def clear_vram():
    gc.collect()
    torch.cuda.empty_cache()


def process_pdf(pdf_path):
    device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"讀取 PDF: {pdf_path}")
    images = convert_from_path(pdf_path, dpi=200)

    print("正在載入 Surya 佈局檢測模型...")
    layout_model = load_layout_model().to(device)
    det_model = load_det_model()
    layout_processor = load_layout_processor()

    all_page_layouts = []
    for idx,img in enumerate(images):
        print(f"分析第{idx +1}頁")
        with torch.no_grad():
            layout_preds = run_layout_detection([img.convert("RGB")], layout_model, layout_processor, det_model)
            all_page_layouts.append(layout_preds[0])

    del layout_model, det_model, layout_processor
    clear_vram()

    print("正在載入 InternVL2 (4-bit 量化)...")
    model_path = "OpenGVLab/InternVL2-8B" 
    model = AutoModel.from_pretrained(
        model_path,
        torch_dtype=torch.bfloat16,
        load_in_4bit=True,          # 必須開啟，否則 8GB 會 OOM (記憶體溢出)
        trust_remote_code=True,
        device_map="auto",
        low_cpu_mem_usage=True           # 自動分配權重
    ).eval()

    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)

    for page_idx , layout in enumerate(all_page_layouts):
        print(f"---處理第 {page_idx+1} 頁---")
        page_img = images[page_idx].convert("RGB")

        for box_idx , box in enumerate(layout.bboxes):
            crop_img = page_img.crop((box.bbox[0], box.bbox[1], box.bbox[2], box.bbox[3]))
            label = box.label
            if label == 'Table':
                prompt = "請將此圖片中的表格內容提取為標準 JSON 格式。"
            else:
                prompt = f"請提取此 {label} 區域內的文字。"

            response, _ = model.chat(tokenizer, crop_img, prompt, generation_config=dict(max_new_tokens=512))
            
            print(f"\n[頁 {page_idx+1} | 區域 {box_idx} | {label}]:")
            print(response)

    del model
    clear_vram()

if __name__ == "__main__":
    import os
    target_pdf = "test01.pdf" 
    if os.path.exists(target_pdf):
        process_pdf(target_pdf)
    else:
        print(f"找不到檔案: {target_pdf}，請確認檔案已放在 C:\\Users\\CiRou\\.00_Dev\\OCR_test\\Docling 目錄下。")

# 執行測試
# process_ocr_task("your_purchase_order.jpg")