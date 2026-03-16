import torch
from transformers import Qwen2VLForConditionalGeneration, Qwen2VLProcessor
from PIL import Image
import pandas as pd
from pdf2image import convert_from_path
import os
from pathlib import Path

# ====================== 1. 載入模型（地端 4-bit 量化） ======================
processor = Qwen2VLProcessor.from_pretrained("Qwen/Qwen2-VL-7B-Instruct")
model = Qwen2VLForConditionalGeneration.from_pretrained(
    "Qwen/Qwen2-VL-7B-Instruct",
    device_map="auto",          # GPU 自動，無 GPU 自動切 CPU
    torch_dtype=torch.float16,
    load_in_4bit=True,          # 極省記憶體
    attn_implementation="flash_attention_2"  # 加速
)

# ====================== 2. PDF / JPG 統一轉圖片 ======================
def pdf_to_images(pdf_path: str):
    images = convert_from_path(pdf_path, dpi=300)  # 高解析度，表格更準
    return images

def process_file(file_path: str):
    if file_path.lower().endswith('.pdf'):
        images = pdf_to_images(file_path)
    else:
        images = [Image.open(file_path).convert("RGB")]
    return images

# ====================== 3. 核心：圖片 → 視覺 token（這就是你問的 Visual Encoder！） ======================
def image_to_excel(file_path: str, output_excel: str = "output.xlsx"):
    images = process_file(file_path)
    all_dfs = []

    for i, image in enumerate(images):
        print(f"處理第 {i+1} 頁...")

        # Prompt：強制輸出結構化表格（LLM 直接生成 CSV 或 JSON）
        conversation = [
            {"role": "user", "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": "請完整提取圖片中所有文字與表格，保持原始排版，輸出為純 CSV 格式（第一行是欄位名稱），如果有多個表格請用分隔線 --- 分開。不要加任何解釋。"}
            ]}
        ]

        text = processor.apply_chat_template(conversation, tokenize=False)
        inputs = processor(
            text=[text],
            images=[image],
            return_tensors="pt",
            padding=True
        ).to(model.device)

        # 生成（視覺 token 已自動由 ViT + MLP Projector 轉成 LLM 可懂的 embeddings）
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=1024,
            temperature=0.0,      # OCR 必須零溫度
            do_sample=False,
            pad_token_id=processor.tokenizer.pad_token_id
        )

        response = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        # 清理 LLM 輸出的 CSV（去除 markdown 包圍）
        csv_text = response.split("```csv")[-1].split("```")[0].strip()
        
        # 轉成 DataFrame
        try:
            df = pd.read_csv(pd.compat.StringIO(csv_text))
            all_dfs.append(df)
            print(f"第 {i+1} 頁提取成功，形狀：{df.shape}")
        except:
            print("CSV 解析失敗，改用純文字備份")
            all_dfs.append(pd.DataFrame({"raw_text": [response]}))

    # ====================== 4. 合併所有頁面並存成 Excel ======================
    if len(all_dfs) > 1:
        final_df = pd.concat(all_dfs, ignore_index=True)
    else:
        final_df = all_dfs[0]

    final_df.to_excel(output_excel, index=False, engine='openpyxl')
    print(f"✅ 轉換完成！檔案已儲存為：{output_excel}")

# ====================== 使用範例 ======================
if __name__ == "__main__":
    file_path = r"C:\Users\CiRou\.00_Dev\OCR_20251230\src\document\MVEV2UM90190225009849.pdf"
    image_to_excel(file_path, "result.xlsx")