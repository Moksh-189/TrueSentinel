import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split, Dataset
from torchvision import datasets, transforms, models
import kagglehub
from tqdm import tqdm
import copy

# Configuration
DATASET_NAME = "xhlulu/140k-real-and-fake-faces"
MODEL_SAVE_PATH = "deepfake_model_densenet.pt"
BEST_MODEL_SAVE_PATH = "deepfake_model_densenet_best.pt"
BATCH_SIZE = 32
EPOCHS = 10
LEARNING_RATE = 0.001
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

class TransformedSubset(Dataset):
    """Wrapper to apply transforms to a Subset of a dataset."""
    def __init__(self, subset, transform=None):
        self.subset = subset
        self.transform = transform
        
    def __getitem__(self, index):
        x, y = self.subset[index]
        if self.transform:
            x = self.transform(x)
        return x, y
    
    def __len__(self):
        return len(self.subset)

def download_dataset():
    print("Downloading dataset from Kaggle... (You may need to authenticate)")
    path = kagglehub.dataset_download(DATASET_NAME)
    print(f"Dataset downloaded to: {path}")
    return path

def train_model(data_dir):
    print(f"Using device: {DEVICE}")
    
    # 1. Define Transforms
    # Training: Robust Augmentation
    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.1, contrast=0.1, saturation=0.1, hue=0.1),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    # Validation: Standard Resize & Normalize
    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    # 2. Locate Data
    train_dir = None
    for root, dirs, files in os.walk(data_dir):
        if "train" in dirs:
            train_dir = os.path.join(root, "train")
            break
    
    if not train_dir or not os.path.exists(train_dir):
        print(f"ERROR: Could not find 'train' folder in {data_dir}")
        return
    
    print(f"Training data directory: {train_dir}")
    
    # 3. Load & Split Dataset
    # Load without transforms first so we can apply different ones to splits
    full_dataset = datasets.ImageFolder(train_dir)
    print(f"Found {len(full_dataset)} total images.")
    print(f"Classes: {full_dataset.classes}")
    
    train_size = int(0.8 * len(full_dataset))
    val_size = len(full_dataset) - train_size
    print(f"Splitting into {train_size} training and {val_size} validation samples.")
    
    train_subset, val_subset = random_split(full_dataset, [train_size, val_size])
    
    # Apply transforms using wrapper
    train_dataset = TransformedSubset(train_subset, transform=train_transform)
    val_dataset = TransformedSubset(val_subset, transform=val_transform)
    
    # 4. Create DataLoaders
    # Optimize for hardware
    num_workers = min(4, os.cpu_count() or 1)
    pin_memory = (DEVICE == "cuda")
    
    train_loader = DataLoader(
        train_dataset, batch_size=BATCH_SIZE, shuffle=True, 
        num_workers=num_workers, pin_memory=pin_memory, persistent_workers=(num_workers > 0)
    )
    val_loader = DataLoader(
        val_dataset, batch_size=BATCH_SIZE, shuffle=False, 
        num_workers=num_workers, pin_memory=pin_memory, persistent_workers=(num_workers > 0)
    )
    
    # 5. Model Setup
    model = models.densenet121(weights=models.DenseNet121_Weights.IMAGENET1K_V1)
    
    num_ftrs = model.classifier.in_features
    model.classifier = nn.Sequential(
        nn.Linear(num_ftrs, 512),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(512, 2)
    )
    
    model = model.to(DEVICE)
    
    # Resume?
    if os.path.exists(MODEL_SAVE_PATH):
        try:
            print(f"Resuming from checkpoint: {MODEL_SAVE_PATH}")
            state_dict = torch.load(MODEL_SAVE_PATH, map_location=DEVICE)
            model.load_state_dict(state_dict)
        except Exception as e:
            print(f"Could not load checkpoint: {e}. Starting fresh.")
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.1, patience=2, verbose=True)
    
    # 6. Training Loop
    best_val_loss = float('inf')
    
    print("Starting training...")
    for epoch in range(EPOCHS):
        # --- TRAINING ---
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0
        
        train_bar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{EPOCHS} [Train]")
        for inputs, labels in train_bar:
            inputs, labels = inputs.to(DEVICE), labels.to(DEVICE)
            
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item() * inputs.size(0)
            _, predicted = torch.max(outputs, 1)
            train_total += labels.size(0)
            train_correct += (predicted == labels).sum().item()
            
            train_bar.set_postfix({'loss': f'{loss.item():.4f}'})
            
        epoch_train_loss = train_loss / len(train_dataset)
        epoch_train_acc = 100 * train_correct / train_total
        
        # --- VALIDATION ---
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        
        print("Validating...")
        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs, labels = inputs.to(DEVICE), labels.to(DEVICE)
                outputs = model(inputs)
                loss = criterion(outputs, labels)
                
                val_loss += loss.item() * inputs.size(0)
                _, predicted = torch.max(outputs, 1)
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()
                
        epoch_val_loss = val_loss / len(val_dataset)
        epoch_val_acc = 100 * val_correct / val_total
        
        print(f"Epoch {epoch+1} Result:")
        print(f"Train Loss: {epoch_train_loss:.4f} | Train Acc: {epoch_train_acc:.2f}%")
        print(f"Val   Loss: {epoch_val_loss:.4f} | Val   Acc: {epoch_val_acc:.2f}%")
        
        # Step Scheduler
        scheduler.step(epoch_val_loss)
        
        # Save Checkpoint (Best & Latest)
        torch.save(model.state_dict(), MODEL_SAVE_PATH) # Save latest
        
        if epoch_val_loss < best_val_loss:
            print(f"Validation loss improved ({best_val_loss:.4f} -> {epoch_val_loss:.4f}). Saving best model...")
            best_val_loss = epoch_val_loss
            torch.save(model.state_dict(), BEST_MODEL_SAVE_PATH)
        
        print("-" * 50)

    print("Training Complete.")
    print(f"Best Validation Loss: {best_val_loss:.4f}")
    print(f"Best model saved to: {BEST_MODEL_SAVE_PATH}")

if __name__ == "__main__":
    data_path = download_dataset()
    train_model(data_path)
