"""
TrustSentinel Deepfake Model Training Script (ResNext + LSTM)
==============================================================
Trains a ResNext50 CNN + LSTM model for video deepfake detection.
Based on: https://github.com/abhijithjadhav/Deepfake_detection_using_deep_learning

Architecture:
- ResNext50 (pretrained) for spatial feature extraction from frames
- LSTM for temporal sequence modeling across video frames
- Binary classification: Real (0) vs Fake (1)
"""

import os
import glob
import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from torchvision.models import resnext50_32x4d, ResNeXt50_32X4D_Weights
from sklearn.model_selection import train_test_split
from tqdm import tqdm
import random

# =============================================================================
# CONFIGURATION
# =============================================================================

# Dataset paths - Update these based on your FaceForensics++ location
DATASET_PATH = r"..\FaceForensics"  # Will contain original and manipulated folders
MODEL_SAVE_PATH = "deepfake_model_resnext_lstm.pt"

# Training parameters
SEQUENCE_LENGTH = 20      # Number of frames per video sequence
BATCH_SIZE = 4            # Small batch due to memory constraints
NUM_EPOCHS = 30           # Training epochs
LEARNING_RATE = 1e-4
NUM_WORKERS = 0           # Windows compatibility
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Image preprocessing
IMAGE_SIZE = 224  # ResNext input size


# =============================================================================
# MODEL ARCHITECTURE: ResNext + LSTM
# =============================================================================

class ResNextLSTM(nn.Module):
    """
    Deepfake Detection Model using ResNext50 + LSTM.
    
    ResNext50 extracts spatial features from individual frames.
    LSTM processes the sequence of features to capture temporal patterns.
    """
    
    def __init__(self, num_classes=2, lstm_hidden=256, lstm_layers=2, dropout=0.3):
        super(ResNextLSTM, self).__init__()
        
        # Load pretrained ResNext50
        self.cnn = resnext50_32x4d(weights=ResNeXt50_32X4D_Weights.IMAGENET1K_V1)
        
        # Freeze early layers for transfer learning
        for param in list(self.cnn.parameters())[:-20]:
            param.requires_grad = False
        
        # Get feature dimension (before final FC layer)
        self.feature_dim = self.cnn.fc.in_features  # 2048
        
        # Replace classification head with identity
        self.cnn.fc = nn.Identity()
        
        # LSTM for temporal modeling
        self.lstm = nn.LSTM(
            input_size=self.feature_dim,
            hidden_size=lstm_hidden,
            num_layers=lstm_layers,
            batch_first=True,
            dropout=dropout if lstm_layers > 1 else 0,
            bidirectional=True
        )
        
        # Classification head
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(lstm_hidden * 2, 128),  # *2 for bidirectional
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, num_classes)
        )
    
    def forward(self, x):
        """
        Forward pass.
        
        Args:
            x: Tensor of shape (batch, sequence, channels, height, width)
        
        Returns:
            Logits of shape (batch, num_classes)
        """
        batch_size, seq_len, C, H, W = x.shape
        
        # Reshape for CNN processing: (batch * seq, C, H, W)
        x = x.view(batch_size * seq_len, C, H, W)
        
        # Extract spatial features
        features = self.cnn(x)  # (batch * seq, feature_dim)
        
        # Reshape back: (batch, seq, feature_dim)
        features = features.view(batch_size, seq_len, -1)
        
        # LSTM temporal processing
        lstm_out, _ = self.lstm(features)  # (batch, seq, hidden*2)
        
        # Use last timestep output for classification
        last_output = lstm_out[:, -1, :]
        
        # Classify
        logits = self.classifier(last_output)
        
        return logits


# =============================================================================
# DATASET CLASS
# =============================================================================

class DeepfakeVideoDataset(Dataset):
    """
    Dataset for loading video sequences for deepfake detection.
    """
    
    def __init__(self, video_paths, labels, seq_length=20, transform=None):
        self.video_paths = video_paths
        self.labels = labels
        self.seq_length = seq_length
        self.transform = transform or self._default_transform()
    
    def _default_transform(self):
        return transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
    
    def __len__(self):
        return len(self.video_paths)
    
    def __getitem__(self, idx):
        video_path = self.video_paths[idx]
        label = self.labels[idx]
        
        # Extract frames
        frames = self._extract_frames(video_path)
        
        if len(frames) == 0:
            # Return black frames if video can't be read
            frames = [torch.zeros(3, IMAGE_SIZE, IMAGE_SIZE) for _ in range(self.seq_length)]
        
        # Stack frames into sequence
        frames_tensor = torch.stack(frames)  # (seq, C, H, W)
        
        return frames_tensor, label
    
    def _extract_frames(self, video_path):
        """Extract uniformly sampled frames from video."""
        frames = []
        
        try:
            cap = cv2.VideoCapture(video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if total_frames <= 0:
                cap.release()
                return frames
            
            # Uniform sampling
            if total_frames >= self.seq_length:
                indices = np.linspace(0, total_frames - 1, self.seq_length, dtype=int)
            else:
                # Repeat frames if video is too short
                indices = list(range(total_frames))
                while len(indices) < self.seq_length:
                    indices.append(indices[-1])
            
            for idx in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if ret:
                    # Convert BGR to RGB
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Detect and crop face (optional, simplified)
                    frame = self._crop_center(frame)
                    
                    # Apply transforms
                    frame_tensor = self.transform(frame)
                    frames.append(frame_tensor)
            
            cap.release()
            
        except Exception as e:
            print(f"Error processing {video_path}: {e}")
        
        return frames
    
    def _crop_center(self, frame, crop_ratio=0.7):
        """Center crop the frame to focus on face region."""
        h, w = frame.shape[:2]
        new_h, new_w = int(h * crop_ratio), int(w * crop_ratio)
        top = (h - new_h) // 2
        left = (w - new_w) // 2
        return frame[top:top+new_h, left:left+new_w]


# =============================================================================
# DATA LOADING
# =============================================================================

def collect_dataset():
    """
    Collect video paths and labels from FaceForensics++ dataset.
    
    Expected structure:
    FaceForensics/
    ├── original_sequences/
    │   └── youtube/
    │       └── c40/
    │           └── videos/
    │               └── *.mp4
    └── manipulated_sequences/
        └── Deepfakes/
            └── c40/
                └── videos/
                    └── *.mp4
    """
    print("\n" + "=" * 60)
    print("Collecting FaceForensics++ Dataset")
    print("=" * 60)
    
    video_paths = []
    labels = []
    
    # Real videos (original sequences)
    real_patterns = [
        os.path.join(DATASET_PATH, "original_sequences", "youtube", "c40", "videos", "*.mp4"),
        os.path.join(DATASET_PATH, "original_sequences", "youtube", "c23", "videos", "*.mp4"),
        os.path.join(DATASET_PATH, "original_sequences", "**", "*.mp4"),
        os.path.join(DATASET_PATH, "original", "**", "*.mp4"),
        os.path.join(DATASET_PATH, "real", "**", "*.mp4"),
        # Fallback to DeepfakeTIMIT if FaceForensics not found
        os.path.join(r"..\DeepfakeTIMIT", "*original*.mov"),
    ]
    
    real_videos = []
    for pattern in real_patterns:
        found = glob.glob(pattern, recursive=True)
        real_videos.extend(found)
        if found:
            print(f"  Found {len(found)} real videos in: {pattern}")
    
    # Remove duplicates
    real_videos = list(set(real_videos))
    print(f"Total real videos: {len(real_videos)}")
    
    # Fake videos (manipulated sequences)
    fake_patterns = [
        os.path.join(DATASET_PATH, "manipulated_sequences", "Deepfakes", "c40", "videos", "*.mp4"),
        os.path.join(DATASET_PATH, "manipulated_sequences", "Deepfakes", "c23", "videos", "*.mp4"),
        os.path.join(DATASET_PATH, "manipulated_sequences", "**", "*.mp4"),
        os.path.join(DATASET_PATH, "fake", "**", "*.mp4"),
        os.path.join(DATASET_PATH, "manipulated", "**", "*.mp4"),
        # Fallback patterns for various dataset structures
        os.path.join(DATASET_PATH, "**", "fake", "*.mp4"),
        os.path.join(DATASET_PATH, "**", "Deepfakes", "*.mp4"),
        # DeepfakeTIMIT fallback
        os.path.join(r"..\DeepfakeTIMIT", "higher_quality", "*", "*.avi"),
        os.path.join(r"..\DeepfakeTIMIT", "lower_quality", "*", "*.avi"),
    ]
    
    fake_videos = []
    for pattern in fake_patterns:
        found = glob.glob(pattern, recursive=True)
        fake_videos.extend(found)
        if found:
            print(f"  Found {len(found)} fake videos in: {pattern}")
    
    # Remove duplicates
    fake_videos = list(set(fake_videos))
    print(f"Total fake videos: {len(fake_videos)}")
    
    # Balance dataset
    min_count = min(len(real_videos), len(fake_videos))
    if min_count == 0:
        print("\nNo videos found! Please check dataset path.")
        print(f"Expected path: {os.path.abspath(DATASET_PATH)}")
        return [], []
    
    # Sample equal numbers
    if len(real_videos) > min_count:
        real_videos = random.sample(real_videos, min_count)
    if len(fake_videos) > min_count:
        fake_videos = random.sample(fake_videos, min_count)
    
    # Combine
    for v in real_videos:
        video_paths.append(v)
        labels.append(0)  # Real
    
    for v in fake_videos:
        video_paths.append(v)
        labels.append(1)  # Fake
    
    print(f"\nFinal dataset: {len(video_paths)} videos ({min_count} real, {min_count} fake)")
    
    return video_paths, labels


# =============================================================================
# TRAINING
# =============================================================================

def train_model():
    """Main training function."""
    print("\n" + "=" * 60)
    print("TrustSentinel ResNext + LSTM Deepfake Detection Training")
    print("=" * 60)
    print(f"Device: {DEVICE}")
    print(f"PyTorch version: {torch.__version__}")
    
    # Collect data
    video_paths, labels = collect_dataset()
    
    if len(video_paths) < 10:
        print("Not enough data for training!")
        return
    
    # Split data
    train_paths, val_paths, train_labels, val_labels = train_test_split(
        video_paths, labels, test_size=0.2, random_state=42, stratify=labels
    )
    
    print(f"\nTraining set: {len(train_paths)} videos")
    print(f"Validation set: {len(val_paths)} videos")
    
    # Create datasets
    train_transform = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize((IMAGE_SIZE + 20, IMAGE_SIZE + 20)),
        transforms.RandomCrop(IMAGE_SIZE),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.1, contrast=0.1),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    val_transform = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    train_dataset = DeepfakeVideoDataset(train_paths, train_labels, SEQUENCE_LENGTH, train_transform)
    val_dataset = DeepfakeVideoDataset(val_paths, val_labels, SEQUENCE_LENGTH, val_transform)
    
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=NUM_WORKERS)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=NUM_WORKERS)
    
    # Create model
    print("\nInitializing ResNext + LSTM model...")
    model = ResNextLSTM(num_classes=2).to(DEVICE)
    
    # Count parameters
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Total parameters: {total_params:,}")
    print(f"Trainable parameters: {trainable_params:,}")
    
    # Loss and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=LEARNING_RATE,
        weight_decay=0.01
    )
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', patience=5, factor=0.5)
    
    # Training loop
    best_val_acc = 0.0
    
    for epoch in range(NUM_EPOCHS):
        print(f"\nEpoch {epoch + 1}/{NUM_EPOCHS}")
        print("-" * 40)
        
        # Training phase
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0
        
        pbar = tqdm(train_loader, desc="Training")
        for frames, labels_batch in pbar:
            frames = frames.to(DEVICE)
            labels_batch = labels_batch.to(DEVICE)
            
            optimizer.zero_grad()
            outputs = model(frames)
            loss = criterion(outputs, labels_batch)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            _, predicted = outputs.max(1)
            train_total += labels_batch.size(0)
            train_correct += predicted.eq(labels_batch).sum().item()
            
            pbar.set_postfix({
                'loss': f'{loss.item():.4f}',
                'acc': f'{100.*train_correct/train_total:.2f}%'
            })
        
        train_acc = 100. * train_correct / train_total
        
        # Validation phase
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        
        with torch.no_grad():
            for frames, labels_batch in tqdm(val_loader, desc="Validation"):
                frames = frames.to(DEVICE)
                labels_batch = labels_batch.to(DEVICE)
                
                outputs = model(frames)
                loss = criterion(outputs, labels_batch)
                
                val_loss += loss.item()
                _, predicted = outputs.max(1)
                val_total += labels_batch.size(0)
                val_correct += predicted.eq(labels_batch).sum().item()
        
        val_acc = 100. * val_correct / val_total
        avg_val_loss = val_loss / len(val_loader)
        
        print(f"Train Loss: {train_loss/len(train_loader):.4f} | Train Acc: {train_acc:.2f}%")
        print(f"Val Loss: {avg_val_loss:.4f} | Val Acc: {val_acc:.2f}%")
        
        # Learning rate scheduling
        scheduler.step(avg_val_loss)
        
        # Save best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            print(f"New best model! Saving to {MODEL_SAVE_PATH}")
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_acc': val_acc,
                'val_loss': avg_val_loss
            }, MODEL_SAVE_PATH)
    
    print("\n" + "=" * 60)
    print("Training Complete!")
    print(f"Best Validation Accuracy: {best_val_acc:.2f}%")
    print(f"Model saved at: {os.path.abspath(MODEL_SAVE_PATH)}")
    print("=" * 60)


if __name__ == "__main__":
    train_model()
