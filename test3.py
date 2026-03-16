# 自訂 hybrid Visual Encoder（ResNet CNN + LSTM RNN）
import torch.nn as nn
from torchvision.models import resnet50
from timm import create_model

class CustomVisualEncoder(nn.Module):
    def __init__(self, llm_embed_dim=4096):
        super().__init__()
        # CNN: ResNet50（預訓練）
        self.cnn = resnet50(pretrained=True)
        self.cnn = nn.Sequential(*list(self.cnn.children())[:-2])  # 去掉最後 FC
        
        # RNN: BiLSTM 處理序列特徵（模擬 CRNN）
        self.rnn = nn.LSTM(2048, 1024, bidirectional=True, batch_first=True)
        
        # Projector: MLP 把 CNN+RNN 特徵轉成 LLM token
        self.projector = nn.Sequential(
            nn.Linear(2048, llm_embed_dim),
            nn.GELU(),
            nn.Linear(llm_embed_dim, llm_embed_dim)
        )
    
    def forward(self, images):
        # CNN 特徵圖
        features = self.cnn(images)  # [B, 2048, H/32, W/32]
        features = features.flatten(2).transpose(1, 2)  # [B, seq_len, 2048]
        
        # RNN 序列建模
        rnn_out, _ = self.rnn(features)
        pooled = rnn_out.mean(dim=1)  # [B, 2048]
        
        # 轉成 LLM token
        visual_tokens = self.projector(pooled)
        return visual_tokens.unsqueeze(1)  # [B, 1, embed_dim] 可擴展成多 token

# 使用方式：把 CustomVisualEncoder 取代 Qwen 的 ViT（需自己寫 Vision2Seq 模型，訓練 projector）
# 這部分需要 LoRA 微調 + 大量圖文對資料，建議先用上面 Qwen 版本。