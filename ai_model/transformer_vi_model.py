"""
Transformer 기반 VI 반등 예측 모델
- Input: VI 전후 60초 틱 데이터 (시계열)
- Output: 반등 확률, 예상 수익률, 최적 진입 타이밍
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from torch.utils.data import Dataset, DataLoader
import pandas as pd
from pathlib import Path


class VISequenceDataset(Dataset):
    """VI 이벤트 시계열 데이터셋"""
    
    def __init__(self, vi_events_dir, sequence_length=60):
        """
        Args:
            vi_events_dir: VI 이벤트 디렉토리 (각 파일 = 1 VI 이벤트)
            sequence_length: 시퀀스 길이 (초 단위, 전후 60초 = 120초)
        """
        self.sequence_length = sequence_length
        self.vi_files = list(Path(vi_events_dir).glob('*.parquet'))
        
        print(f"✅ {len(self.vi_files)}개 VI 이벤트 로드")
    
    def __len__(self):
        return len(self.vi_files)
    
    def __getitem__(self, idx):
        """
        Returns:
            features: (120, 21) - 120초 × 21개 feature
            label: (3,) - [반등여부, 수익률, 진입타이밍]
        """
        # VI 이벤트 파일 로드
        df = pd.read_parquet(self.vi_files[idx])
        
        # Feature 추출
        features = self._extract_features(df)
        
        # Label 추출 (VI 해제 후 30초 기준)
        label = self._extract_label(df)
        
        return torch.FloatTensor(features), torch.FloatTensor(label)
    
    def _extract_features(self, df):
        """
        21개 feature 추출
        
        Features:
          1. 정규화된 가격 (close_norm)
          2. 거래량 (volume_norm)
          3-12. 매수호가 1~10 (bid_price_1~10_norm)
          13-22. 매도호가 1~10 (ask_price_1~10_norm)
          23. 프로그램 순매수 (program_net_norm)
          24. 기관 순매수 (institution_net_norm)
          25. 외국인 순매수 (foreign_net_norm)
          26. VI 상태 (0=정상, 1=발동, 2=해제)
        
        Returns:
            (120, 26) numpy array
        """
        # 120초 슬라이싱 (VI 전 60초 + 후 60초)
        vi_idx = df[df['vi_status'] == 1].index[0]  # VI 발동 시점
        start_idx = max(0, vi_idx - 60)
        end_idx = min(len(df), vi_idx + 60)
        
        df_slice = df.iloc[start_idx:end_idx]
        
        # Feature 정규화
        features = []
        
        # 가격 (MinMax 정규화)
        price_norm = (df_slice['price'] - df_slice['price'].min()) / \
                     (df_slice['price'].max() - df_slice['price'].min() + 1e-8)
        features.append(price_norm.values)
        
        # 거래량 (Log 정규화)
        volume_norm = np.log1p(df_slice['volume']) / 10.0
        features.append(volume_norm.values)
        
        # 호가 (상대적 거리)
        for i in range(1, 11):
            bid_norm = (df_slice[f'bid_price_{i}'] - df_slice['price']) / df_slice['price']
            ask_norm = (df_slice[f'ask_price_{i}'] - df_slice['price']) / df_slice['price']
            features.append(bid_norm.values)
            features.append(ask_norm.values)
        
        # 프로그램/기관/외국인 (표준화)
        for col in ['program_net_buy', 'institution_net', 'foreign_net']:
            values = df_slice[col].values
            norm = (values - values.mean()) / (values.std() + 1e-8)
            features.append(norm)
        
        # VI 상태 (원핫 인코딩)
        vi_status = df_slice['vi_status'].values / 2.0  # 0~1 범위
        features.append(vi_status)
        
        # (26, 120) → (120, 26) 전치
        features = np.array(features).T
        
        # 120초 미만이면 패딩
        if len(features) < 120:
            pad = np.zeros((120 - len(features), 26))
            features = np.vstack([features, pad])
        
        return features[:120]  # 정확히 120초
    
    def _extract_label(self, df):
        """
        Label 추출
        
        Returns:
            [반등여부, 수익률, 진입타이밍]
            
            - 반등여부: VI 해제 후 30초 내 2% 이상 상승 → 1, 아니면 0
            - 수익률: VI 해제가 대비 30초 후 최고가 수익률
            - 진입타이밍: 최고 수익률을 기록한 시점 (0~29초)
        """
        vi_idx = df[df['vi_status'] == 1].index[0]
        release_idx = df[df['vi_status'] == 2].index[0]  # VI 해제
        
        # VI 해제 후 30초
        after_release = df.iloc[release_idx:release_idx+30]
        
        if len(after_release) == 0:
            return np.array([0.0, 0.0, 0.0])
        
        entry_price = df.iloc[release_idx]['price']
        max_price = after_release['price'].max()
        max_idx = after_release['price'].idxmax()
        
        # 수익률
        profit_rate = (max_price - entry_price) / entry_price
        
        # 반등 여부 (2% 이상)
        rebound = 1.0 if profit_rate > 0.02 else 0.0
        
        # 진입 타이밍 (0~29초)
        entry_timing = min(max_idx - release_idx, 29) / 29.0  # 정규화
        
        return np.array([rebound, profit_rate, entry_timing])


class PositionalEncoding(nn.Module):
    """위치 인코딩 (시계열 순서 정보)"""
    
    def __init__(self, d_model, max_len=120):
        super().__init__()
        
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * 
                             (-np.log(10000.0) / d_model))
        
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        
        self.register_buffer('pe', pe.unsqueeze(0))
    
    def forward(self, x):
        return x + self.pe[:, :x.size(1)]


class VITransformerModel(nn.Module):
    """
    Transformer 기반 VI 반등 예측 모델
    
    Architecture:
      1. Input Embedding: (120, 26) → (120, 256)
      2. Positional Encoding
      3. Transformer Encoder (6 layers)
      4. Multi-Head Output:
         - 반등 확률 (Binary Classification)
         - 예상 수익률 (Regression)
         - 진입 타이밍 (Regression, 0~1)
    """
    
    def __init__(self, input_dim=26, d_model=256, nhead=8, num_layers=6, dropout=0.1):
        super().__init__()
        
        # Input Embedding
        self.embedding = nn.Linear(input_dim, d_model)
        
        # Positional Encoding
        self.pos_encoder = PositionalEncoding(d_model)
        
        # Transformer Encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=1024,
            dropout=dropout,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # Global Average Pooling
        self.pool = nn.AdaptiveAvgPool1d(1)
        
        # Multi-Head Output
        self.rebound_head = nn.Sequential(
            nn.Linear(d_model, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, 1),
            nn.Sigmoid()  # 확률 (0~1)
        )
        
        self.profit_head = nn.Sequential(
            nn.Linear(d_model, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, 1)  # 수익률 (실수)
        )
        
        self.timing_head = nn.Sequential(
            nn.Linear(d_model, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, 1),
            nn.Sigmoid()  # 타이밍 (0~1)
        )
    
    def forward(self, x):
        """
        Args:
            x: (batch_size, 120, 26) - VI 전후 60초 시계열
        
        Returns:
            dict: {
                'rebound_prob': (batch_size, 1),
                'expected_profit': (batch_size, 1),
                'entry_timing': (batch_size, 1)
            }
        """
        # Embedding
        x = self.embedding(x)  # (B, 120, 256)
        
        # Positional Encoding
        x = self.pos_encoder(x)
        
        # Transformer
        x = self.transformer(x)  # (B, 120, 256)
        
        # Global Average Pooling
        x = x.transpose(1, 2)  # (B, 256, 120)
        x = self.pool(x).squeeze(-1)  # (B, 256)
        
        # Multi-Head Prediction
        rebound_prob = self.rebound_head(x)
        expected_profit = self.profit_head(x)
        entry_timing = self.timing_head(x)
        
        return {
            'rebound_prob': rebound_prob,
            'expected_profit': expected_profit,
            'entry_timing': entry_timing
        }


class VIModelTrainer:
    """모델 학습 클래스"""
    
    def __init__(self, model, device='cuda'):
        self.model = model.to(device)
        self.device = device
        
        # 멀티태스크 손실 함수
        self.criterion_rebound = nn.BCELoss()  # 반등 여부
        self.criterion_profit = nn.MSELoss()   # 수익률
        self.criterion_timing = nn.MSELoss()   # 타이밍
        
        # Optimizer
        self.optimizer = torch.optim.AdamW(  # type: ignore
            model.parameters(),
            lr=1e-4,
            weight_decay=1e-5
        )
        
        # Learning Rate Scheduler
        self.scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer, T_max=100
        )
    
    def train_epoch(self, train_loader):
        """1 Epoch 학습"""
        self.model.train()
        total_loss = 0
        
        for batch_idx, (features, labels) in enumerate(train_loader):
            features = features.to(self.device)
            labels = labels.to(self.device)
            
            # Forward
            outputs = self.model(features)
            
            # Loss 계산 (멀티태스크)
            loss_rebound = self.criterion_rebound(
                outputs['rebound_prob'], 
                labels[:, 0:1]
            )
            loss_profit = self.criterion_profit(
                outputs['expected_profit'], 
                labels[:, 1:2]
            )
            loss_timing = self.criterion_timing(
                outputs['entry_timing'], 
                labels[:, 2:3]
            )
            
            # 가중 합산
            loss = loss_rebound * 0.5 + loss_profit * 0.3 + loss_timing * 0.2
            
            # Backward
            self.optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
            self.optimizer.step()
            
            total_loss += loss.item()
        
        self.scheduler.step()
        return total_loss / len(train_loader)
    
    def evaluate(self, val_loader):
        """검증"""
        self.model.eval()
        total_loss = 0
        correct = 0
        total = 0
        
        with torch.no_grad():
            for features, labels in val_loader:
                features = features.to(self.device)
                labels = labels.to(self.device)
                
                outputs = self.model(features)
                
                # 반등 예측 정확도
                pred_rebound = (outputs['rebound_prob'] > 0.5).float()
                correct += (pred_rebound == labels[:, 0:1]).sum().item()
                total += labels.size(0)
                
                # Loss
                loss_rebound = self.criterion_rebound(
                    outputs['rebound_prob'], labels[:, 0:1]
                )
                loss_profit = self.criterion_profit(
                    outputs['expected_profit'], labels[:, 1:2]
                )
                loss_timing = self.criterion_timing(
                    outputs['entry_timing'], labels[:, 2:3]
                )
                
                loss = loss_rebound * 0.5 + loss_profit * 0.3 + loss_timing * 0.2
                total_loss += loss.item()
        
        accuracy = correct / total
        avg_loss = total_loss / len(val_loader)
        
        return avg_loss, accuracy


def main():
    """학습 실행 예제"""
    
    # Device 설정
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"✅ Device: {device}")
    
    # 데이터셋 로드 (예시 경로)
    train_dataset = VISequenceDataset('./data/vi_events/train')
    val_dataset = VISequenceDataset('./data/vi_events/val')
    
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)
    
    # 모델 생성
    model = VITransformerModel(
        input_dim=26,
        d_model=256,
        nhead=8,
        num_layers=6
    )
    
    print(f"✅ 모델 파라미터 수: {sum(p.numel() for p in model.parameters()):,}")
    
    # 트레이너 생성
    trainer = VIModelTrainer(model, device=device)
    
    # 학습
    best_accuracy = 0
    for epoch in range(100):
        train_loss = trainer.train_epoch(train_loader)
        val_loss, val_accuracy = trainer.evaluate(val_loader)
        
        print(f"Epoch {epoch+1}/100:")
        print(f"  Train Loss: {train_loss:.4f}")
        print(f"  Val Loss: {val_loss:.4f}")
        print(f"  Val Accuracy: {val_accuracy:.2%}")
        
        # Best 모델 저장
        if val_accuracy > best_accuracy:
            best_accuracy = val_accuracy
            torch.save(model.state_dict(), './models/vi_transformer_best.pth')
            print(f"  ✅ Best 모델 저장 (정확도: {best_accuracy:.2%})")
    
    print(f"\n🎉 학습 완료! 최고 정확도: {best_accuracy:.2%}")


if __name__ == '__main__':
    main()
