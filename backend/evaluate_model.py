import torch
import os
import kagglehub
from torchvision import datasets, transforms, models
import torch.nn as nn
from torch.utils.data import DataLoader
from tqdm import tqdm

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

def evaluate():
    print(f"Using device: {DEVICE}")
    print("Locating dataset...")
    path = kagglehub.dataset_download("xhlulu/140k-real-and-fake-faces")
    
    test_dir = None
    for root, dirs, files in os.walk(path):
        if "test" in dirs:
            test_dir = os.path.join(root, "test")
            break
            
    if not test_dir:
        print("Could not find test directory!")
        return

    print(f"Test Set: {test_dir}")
    
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    dataset = datasets.ImageFolder(test_dir, transform=transform)
    # Check classes
    print(f"Classes: {dataset.classes}") # Should be ['fake', 'real']
    
    loader = DataLoader(dataset, batch_size=32, shuffle=False, num_workers=4)
    
    # Load Model
    model = models.densenet121(weights=None)
    num_ftrs = model.classifier.in_features
    model.classifier = nn.Sequential(
        nn.Linear(num_ftrs, 512),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(512, 2)
    )
    
    model_path = "deepfake_model_densenet.pt"
    if not os.path.exists(model_path):
        print(f"Model file {model_path} not found!")
        return
        
    state_dict = torch.load(model_path, map_location=DEVICE)
    model.load_state_dict(state_dict)
    model.to(DEVICE)
    model.eval()
    
    correct = 0
    total = 0
    class_correct = list(0. for i in range(2))
    class_total = list(0. for i in range(2))
    
    print("Evaluating on 20,000 images...")
    with torch.no_grad():
        for inputs, labels in tqdm(loader):
            inputs, labels = inputs.to(DEVICE), labels.to(DEVICE)
            outputs = model(inputs)
            _, predicted = torch.max(outputs, 1)
            
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            
            c = (predicted == labels).squeeze()
            for i in range(len(labels)):
                label = labels[i]
                class_correct[label] += c[i].item()
                class_total[label] += 1
            
    acc = 100 * correct / total
    print(f"\nOverall Test Accuracy: {acc:.2f}%")
    
    for i in range(2):
        print(f"Accuracy of {dataset.classes[i]}: {100 * class_correct[i] / class_total[i]:.2f}%")

if __name__ == "__main__":
    evaluate()
