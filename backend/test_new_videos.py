import os
import requests
import mimetypes

def test_videos(folder_path):
    print(f"Testing videos in: {folder_path}")
    print("-" * 50)
    
    files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.mp4', '.mov', '.avi'))]
    
    for filename in files:
        file_path = os.path.join(folder_path, filename)
        print(f"\nProcessing: {filename}")
        
        try:
            with open(file_path, 'rb') as f:
                files = {'video': (filename, f, mimetypes.guess_type(file_path)[0])}
                response = requests.post('http://localhost:8000/detect-deepfake-video', files=files)
                
            if response.status_code == 200:
                result = response.json()
                status = result.get('status', 'unknown')
                score = result.get('deepfake_score', 0)
                msg = result.get('message', '')
                
                # ANSI colors
                GREEN = '\033[92m'
                RED = '\033[91m'
                RESET = '\033[0m'
                
                color = GREEN if status == 'authentic' else RED
                print(f"Result: {color}{status.upper()}{RESET}")
                print(f"Score: {score:.2f}%")
                print(f"Message: {msg}")
            else:
                print(f"Error: Server returned {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"Failed to process: {str(e)}")

if __name__ == "__main__":
    # Path to the vids folder relative to backend where this script is
    vids_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vids")
    test_videos(vids_path)
