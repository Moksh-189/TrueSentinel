
import requests
import os
import glob
import cv2
import numpy as np
import random
import time
import sys

# Configuration
API_URL = "http://localhost:8000"
DATASET_PATH = r"..\DeepfakeTIMIT"

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def log_pass(message):
    print(f"{GREEN}[PASS]{RESET} {message}")

def log_fail(message):
    print(f"{RED}[FAIL]{RESET} {message}")

def log_info(message):
    print(f"{YELLOW}[INFO]{RESET} {message}")

def get_random_frame(video_path):
    """Extract a random frame from a video file."""
    try:
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            return None
        
        # Pick a frame from the middle
        frame_idx = random.randint(total_frames // 4, 3 * total_frames // 4)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            # Encode as JPEG
            _, buffer = cv2.imencode('.jpg', frame)
            return buffer.tobytes()
    except Exception as e:
        print(f"Error extracting frame: {e}")
    return None

def test_health():
    """Test API Health Endpoint"""
    log_info("Testing /health endpoint...")
    try:
        start = time.time()
        res = requests.get(f"{API_URL}/health")
        duration = time.time() - start
        
        if res.status_code == 200:
            data = res.json()
            log_pass(f"Health check passed in {duration:.3f}s. Status: {data.get('status')} (Mode: {data.get('mode')})")
            return True
        else:
            log_fail(f"Health check failed: {res.status_code} - {res.text}")
            return False
    except Exception as e:
        log_fail(f"Health check connection error: {e}")
        return False

def test_phishing_detection():
    """Test Phishing Detection API"""
    log_info("Testing /check-trust endpoint...")
    
    # Test 1: Safe URL
    safe_url = "https://www.google.com"
    try:
        res = requests.get(f"{API_URL}/check-trust", params={"url": safe_url})
        if res.status_code == 200:
            data = res.json()
            if data['status'] == 'safe':
                log_pass(f"Safe URL correctly identified: {safe_url}")
            else:
                log_fail(f"Safe URL misidentified as {data['status']}: {safe_url}")
        else:
            log_fail(f"API Error on safe URL: {res.status_code}")
    except Exception as e:
        log_fail(f"Connection error: {e}")

    # Test 2: Known Malicious URL (Simulated based on typical params if we don't have a live one, 
    # but we can try a real one from a recent list if available, or just rely on the simulated 'danger' logic checks
    # For this test, we accept 'safe' if the database doesn't have it, but we want to fail if it crashes)
    # Let's try to find a URL that might be in the loaded dataset if possible, or just check that the API responds.
    # We'll use a test URL that we KNOW likely isn't in there but checking the response format is key.
    
    # Actually, let's try a potentially suspicious looking one just to see the response
    sus_url = "http://paypal-secure-login-account-update.com" 
    try:
        res = requests.get(f"{API_URL}/check-trust", params={"url": sus_url})
        if res.status_code == 200:
            data = res.json()
            log_info(f"Suspicious URL check result: {data['status']} (Confidence: {data['confidence']})")
            log_pass("Phishing API response structure verified")
        else:
            log_fail(f"API Error on suspicious URL: {res.status_code}")
    except Exception as e:
        log_fail(f"Connection error: {e}")

def test_deepfake_detection():
    """Test Deepfake Detection API"""
    log_info("Testing /detect-deepfake endpoint...")
    
    # Locate videos
    fake_videos = glob.glob(os.path.join(DATASET_PATH, "higher_quality", "*", "*.avi"))
    real_videos = glob.glob(os.path.join(DATASET_PATH, "*original*.mov"))
    # Recursively look for original sequences if not in root
    if not real_videos:
        real_videos = glob.glob(os.path.join(DATASET_PATH, "original_sequences", "*", "*.avi"))

    if not fake_videos:
        log_fail("No fake videos found in dataset path")
        return
    if not real_videos:
        log_fail("No real videos found in dataset path")
        return

    # Test Real Image
    real_video = random.choice(real_videos)
    log_info(f"Testing Real Sample: {os.path.basename(real_video)}")
    real_img_bytes = get_random_frame(real_video)
    
    if real_img_bytes:
        try:
            files = {'image': ('real.jpg', real_img_bytes, 'image/jpeg')}
            res = requests.post(f"{API_URL}/detect-deepfake", files=files)
            if res.status_code == 200:
                data = res.json()
                score = data.get('deepfake_score', 100)
                status = data.get('status')
                if score < 50:
                    log_pass(f"Real image correctly identified. Score: {score}% (Status: {status})")
                else:
                    log_fail(f"Real image misidentified. Score: {score}% (Status: {status})")
            else:
                log_fail(f"API Error on real image: {res.status_code}")
        except Exception as e:
            log_fail(f"Connection error: {e}")
    else:
        log_fail("Could not extract frame from real video")

    # Test Fake Image
    fake_video = random.choice(fake_videos)
    log_info(f"Testing Fake Sample: {os.path.basename(fake_video)}")
    fake_img_bytes = get_random_frame(fake_video)
    
    if fake_img_bytes:
        try:
            files = {'image': ('fake.jpg', fake_img_bytes, 'image/jpeg')}
            res = requests.post(f"{API_URL}/detect-deepfake", files=files)
            if res.status_code == 200:
                data = res.json()
                score = data.get('deepfake_score', 0)
                status = data.get('status')
                if score > 50:
                    log_pass(f"Fake image correctly identified. Score: {score}% (Status: {status})")
                else:
                    log_fail(f"Fake image misidentified. Score: {score}% (Status: {status})")
            else:
                log_fail(f"API Error on fake image: {res.status_code}")
        except Exception as e:
            log_fail(f"Connection error: {e}")
    else:
        log_fail("Could not extract frame from fake video")

if __name__ == "__main__":
    print("========================================")
    print(" TRUSTSENTINEL SYSTEM VERIFICATION ")
    print("========================================")
    
    if test_health():
        print("\n----------------------------------------")
        test_phishing_detection()
        print("\n----------------------------------------")
        test_deepfake_detection()
    
    print("\n========================================")
    print(" Verification Complete ")
    print("========================================")
