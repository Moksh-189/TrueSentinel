import requests
import os
import time

# Models
MODELS = {
    "umm-maybe": "https://api-inference.huggingface.co/models/umm-maybe/AI-image-detector"
}

def query(filename, api_url):
    with open(filename, "rb") as f:
        data = f.read()
    
    headers = {"Authorization": "Bearer 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"}
    
    for attempt in range(5):
        try:
            response = requests.post(api_url, headers=headers, data=data)
            if response.status_code == 503:
                print(f"Model loading... (Attempt {attempt+1}/5)")
                time.sleep(10)
                continue
            
            try:
                return response.json()
            except:
                return {"error": f"Invalid JSON ({response.status_code}): {response.text[:100]}"}
        except Exception as e:
            return {"error": str(e)}
    return {"error": "Timeout"}

def test():
    img_path = os.path.join("..", "img", "fake_10004.jpg")
    print(f"Testing {img_path}...")
    
    if not os.path.exists(img_path):
        print("File not found.")
        return

    for name, url in MODELS.items():
        print(f"\nQuerying {name}...")
        res = query(img_path, url)
        print(f"Result: {res}")

if __name__ == "__main__":
    test()
