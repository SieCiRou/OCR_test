import torch
from transformers import Qwen2VLForConditionalGeneration, Qwen2VLProcessor
from PIL import Image

# 1. 載入模型與 processor（自動量化 + GPU/CPU 放置）
processor = Qwen2VLProcessor.from_pretrained("Qwen/Qwen2-VL-7B-Instruct")
model = Qwen2VLForConditionalGeneration.from_pretrained(
    "Qwen/Qwen2-VL-7B-Instruct",
    device_map="auto",          # 自動放 GPU，無 GPU 則 CPU
    torch_dtype=torch.float16,  # GPU 用 FP16
    load_in_4bit=True,          # 4-bit 量化，大幅省記憶體
    # 純 CPU 可改 torch_dtype=torch.float32
)

# 2. 準備圖片與 prompt
image = Image.open("your_document.png").convert("RGB")
conversation = [
    {"role": "user", "content": [
        {"type": "image", "image": image},
        {"type": "text", "text": "請提取圖片中所有文字，並保持原始排版與表格結構。"}
    ]}
]

# 3. Processor 自動處理：圖片 → patches → 視覺 token（這就是核心！）
text = processor.apply_chat_template(conversation, tokenize=False)
inputs = processor(
    text=[text],
    images=[image],
    return_tensors="pt",
    padding=True
).to(model.device)

# 4. 生成（視覺 token 已自動注入）
generated_ids = model.generate(
    **inputs,
    max_new_tokens=512,
    temperature=0.1,   # OCR 建議低溫更準
    do_sample=False
)

# 5. 解碼輸出
response = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
print(response)