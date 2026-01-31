# TrustSentinel 🛡️

**Cybersecurity & Digital Trust Platform**

TrustSentinel is a comprehensive security solution featuring two core pillars:
1. **Phishing Shield** - High-speed URL threat detection using Bloom Filters
2. **Bio-Liveness Detector (Deepfake Shield)** - rPPG-based deepfake detection using computer vision

## 🏗️ Architecture

```
TrustSentinel/
├── app/                    # React + Vite Frontend
│   ├── src/
│   │   ├── sections/       # UI sections (Phishing, Deepfake, etc.)
│   │   └── components/     # Reusable UI components
│   └── package.json
├── backend/                # FastAPI Backend
│   ├── main.py            # API endpoints & PhishingDetector
│   └── requirements.txt
├── deepfake_tool/          # Standalone Deepfake Detector
│   ├── sentinel_vision.py # rPPG-based liveness detection
│   └── requirements.txt
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- **Docker** - For Redis with Bloom Filter support
- **Python 3.10+** - For backend and deepfake detection
- **Node.js 18+** - For frontend
- **Webcam** - For deepfake detection demo

### Step 1: Start Redis with Bloom Filter Support

```bash
# Pull and run RedisBloom container
docker run -d --name redis-bloom -p 6379:6379 redislabs/rebloom:latest

# Verify it's running
docker ps
```

### Step 2: Start the Backend API

```bash
# Navigate to backend directory
cd backend

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the API server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will:
1. Connect to Redis
2. Fetch URLHaus malicious URL dataset (~100,000+ URLs)
3. Load URLs into Bloom Filter for O(1) lookups
4. Start serving requests at `http://localhost:8000`

**API Endpoints:**
- `GET /check-trust?url={url}` - Check if URL is malicious
- `GET /health` - Health check with stats
- `GET /` - API info

### Step 3: Start the Frontend

```bash
# Navigate to frontend directory
cd app

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at `http://localhost:5173`

### Step 4: Run Deepfake Detector (Standalone)

```bash
# Navigate to deepfake tool directory
cd deepfake_tool

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the detector
python sentinel_vision.py
```

**Controls:**
- `Q` - Quit
- `R` - Reset signal buffer

---

## 🔧 Technical Details

### Phishing Shield

**How it works:**
1. On startup, fetches the [URLHaus](https://urlhaus.abuse.ch/) dataset (CSV format)
2. Loads malicious URLs into a Redis Bloom Filter
3. When a URL is checked, performs O(1) lookup against the filter

**Bloom Filter Properties:**
- **No false negatives** - If a URL is malicious, it WILL be detected
- **Low false positives** - ~0.1% chance of flagging a safe URL
- **Memory efficient** - ~1.2 bytes per URL
- **O(1) lookups** - Constant time regardless of dataset size

### Bio-Liveness Detector (Deepfake Shield)

**How it works (rPPG - Remote Photoplethysmography):**

1. **Face Detection**: Uses MediaPipe Face Mesh (468 landmarks)
2. **ROI Extraction**: Extracts forehead and cheek regions (high capillary density)
3. **Signal Extraction**: Measures mean Green channel intensity over time
4. **FFT Analysis**: Applies Fast Fourier Transform to find heartbeat frequency
5. **Classification**: Valid heartbeat (0.8-3.0 Hz) = Live human, else = Deepfake

**Why Green Channel?**
Hemoglobin absorbs green light (~550nm) more than red or blue. Blood volume changes with each heartbeat, causing micro-variations in skin color that are strongest in the green channel.

**Mathematical Process:**
```
1. Buffer: Collect 150 frames (~5 seconds at 30fps)
2. Filter: Bandpass 0.7-3.5 Hz to isolate cardiac frequencies
3. FFT: Decompose signal into frequency components
4. Peak Detection: Find dominant frequency in 0.8-3.0 Hz range
5. BPM Calculation: frequency × 60 = beats per minute
```

---

## 📊 API Reference

### POST /check-trust

Check if a URL is potentially malicious.

**Request:**
```
GET /check-trust?url=https://example.com
```

**Response (Safe):**
```json
{
  "status": "safe",
  "confidence": 0.85,
  "url": "https://example.com",
  "domain": "example.com",
  "message": "✓ URL not found in known threat databases"
}
```

**Response (Danger):**
```json
{
  "status": "danger",
  "confidence": 0.95,
  "url": "https://malware-site.xyz",
  "domain": "malware-site.xyz",
  "message": "⚠️ URL found in known malicious database (URLHaus)"
}
```

---

## 🎨 Frontend Features

- **Cyberpunk Aesthetic** - Dark mode with neon accents
- **Real-time Scanning** - Live URL threat detection
- **Animated Shields** - Visual feedback for scan results
- **rPPG Visualization** - Simulated heartbeat waveform display
- **Responsive Design** - Works on desktop and mobile

---

## 🐳 Docker Commands Reference

```bash
# Start Redis with Bloom Filter
docker run -d --name redis-bloom -p 6379:6379 redislabs/rebloom:latest

# Check if running
docker ps

# View logs
docker logs redis-bloom

# Stop container
docker stop redis-bloom

# Remove container
docker rm redis-bloom
```

---

## ⚠️ Troubleshooting

### Backend Issues

**"Failed to connect to Redis"**
- Ensure Docker is running: `docker ps`
- Verify Redis container is up: `docker run -d -p 6379:6379 redislabs/rebloom`

**"Failed to fetch URLHaus dataset"**
- Check internet connection
- URLHaus may be temporarily unavailable
- Backend will start with empty filter (add URLs manually)

### Deepfake Detector Issues

**"Could not open webcam"**
- Ensure webcam is connected
- Close other applications using the camera
- Try a different camera index: edit `cv2.VideoCapture(0)` to `cv2.VideoCapture(1)`

**"No face detected"**
- Ensure good lighting
- Face the camera directly
- Reduce distance from camera

**Inaccurate BPM readings**
- Stay still during measurement
- Ensure consistent lighting
- Wait for buffer to fill (5 seconds)

---

## 🏆 Hackathon Notes

This project was built for a hackathon demonstrating:
- **High-performance** data structures (Bloom Filters)
- **Computer Vision** + signal processing (rPPG)
- **Modern web development** (React + FastAPI)
- **Real-world security** applications

---

## 📄 License

MIT License - Use freely for learning and development.

---

## 👥 Team

Built with ❤️ by the TrustSentinel Team
