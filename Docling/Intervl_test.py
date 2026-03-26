import torch
from transformers import AutoModel, AutoTokenizer
from PIL import Image
import torchvision.transforms as T

model_path = "OpenGVLab/InternVL2_5-8B"

# 1. 載入模型 (使用 4-bit 量化以節省 VRAM)
tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
model = AutoModel.from_pretrained(
    model_path,
    torch_dtype=torch.bfloat16,
    low_cpu_mem_usage=True,
    trust_remote_code=True,
    load_in_4bit=True, # 關鍵：啟用 4-bit 量化
    device_map="auto"
).eval()

def extract_po_data(image_path):
    # 2. 針對採購單場景的 Prompt
    # 特別強調處理無格線表格與單/雙欄位
    prompt = (
        "<image>\n這是一張採購單。請幫我提取圖中的所有資訊。"
        "包含上方的單/雙欄欄位資訊，以及下方的商品表格。"
        "表格即使沒有明確格線，也請根據對齊關係提取數據。"
        "請直接以 JSON 格式輸出，不要有多餘的解釋。"
    )

    image = Image.open(image_path).convert('RGB')
    
    # InternVL2.5 支持動態解析度，適合處理密集文字
    response, history = model.chat(tokenizer, image, prompt, generation_config={"max_new_tokens": 1024})
    return response

# 測試運行
if __name__ == "__main__":
    result = extract_po_data("your_purchase_order.jpg")
    print(result)