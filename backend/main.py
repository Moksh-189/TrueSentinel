"""
TrustSentinel Backend API
=========================
FastAPI-based phishing URL detection using Bloom Filter.
Supports both Redis Bloom Filter (production) and in-memory fallback (demo).

Features:
- Fetches malicious URLs from URLHaus on startup
- O(1) lookup time using Bloom Filter
- Automatic fallback to in-memory filter if Redis unavailable

Author: TrustSentinel Team
"""

import asyncio
import csv
import hashlib
import io
import logging
import math
import os
import random
import shutil
import tempfile
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, validator

# Try to import redis, but don't fail if not available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

# Image deepfake detector import
from deepfake_detector import ImageDeepfakeDetector, DeepfakeCheckResponse

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
BLOOM_FILTER_NAME = "trustsentinel:phishing_urls"
BLOOM_FILTER_ERROR_RATE = 0.001  # 0.1% false positive rate
BLOOM_FILTER_CAPACITY = 500_000  # Expected number of URLs

# URLHaus dataset URL (CSV format with online malicious URLs)
URLHAUS_CSV_URL = "https://urlhaus.abuse.ch/downloads/csv_online/"


# =============================================================================
# RESPONSE MODELS
# =============================================================================
class TrustCheckResponse(BaseModel):
    """Response model for URL trust check"""
    status: str  # "safe" or "danger"
    confidence: float  # 0.0 to 1.0
    url: str
    domain: Optional[str] = None
    message: str


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str
    redis_connected: bool
    bloom_filter_size: int
    message: str
    mode: str  # "redis" or "in-memory"





# =============================================================================
# IN-MEMORY BLOOM FILTER (FALLBACK)
# =============================================================================
class InMemoryBloomFilter:
    """
    Pure Python Bloom Filter implementation for when Redis is unavailable.
    
    Uses multiple hash functions (murmur-style using MD5) to set bits in a bit array.
    Provides O(1) lookup with configurable false positive rate.
    """
    
    def __init__(self, capacity: int, error_rate: float = 0.001):
        """
        Initialize Bloom Filter.
        
        Args:
            capacity: Expected number of elements
            error_rate: Desired false positive rate (0.001 = 0.1%)
        """
        # Calculate optimal size and number of hash functions
        # m = -n * ln(p) / (ln(2)^2)
        # k = (m/n) * ln(2)
        self.capacity = capacity
        self.error_rate = error_rate
        
        # Bit array size
        self.size = self._get_size(capacity, error_rate)
        
        # Number of hash functions
        self.hash_count = self._get_hash_count(self.size, capacity)
        
        # Bit array (using bytearray for memory efficiency)
        self.bit_array = bytearray((self.size + 7) // 8)
        
        # Count of items added
        self.count = 0
        
        logger.info(
            f"InMemoryBloomFilter initialized: "
            f"size={self.size:,} bits, hash_count={self.hash_count}, "
            f"capacity={capacity:,}, error_rate={error_rate}"
        )
    
    def _get_size(self, n: int, p: float) -> int:
        """Calculate optimal bit array size"""
        m = -(n * math.log(p)) / (math.log(2) ** 2)
        return int(math.ceil(m))
    
    def _get_hash_count(self, m: int, n: int) -> int:
        """Calculate optimal number of hash functions"""
        k = (m / n) * math.log(2)
        return int(math.ceil(k))
    
    def _hashes(self, item: str) -> list:
        """
        Generate multiple hash values for an item.
        Uses double hashing technique with MD5 for good distribution.
        """
        # Get two independent hash values
        h1 = int(hashlib.md5(item.encode()).hexdigest(), 16)
        h2 = int(hashlib.sha1(item.encode()).hexdigest(), 16)
        
        # Generate k hash values using double hashing
        # h(i) = h1 + i * h2
        return [(h1 + i * h2) % self.size for i in range(self.hash_count)]
    
    def add(self, item: str) -> None:
        """Add an item to the filter"""
        for pos in self._hashes(item):
            byte_idx = pos // 8
            bit_idx = pos % 8
            self.bit_array[byte_idx] |= (1 << bit_idx)
        self.count += 1
    
    def add_bulk(self, items: list) -> int:
        """Add multiple items at once (vectorized)"""
        added = 0
        for item in items:
            self.add(item)
            added += 1
        return added
    
    def exists(self, item: str) -> bool:
        """Check if an item might be in the filter"""
        for pos in self._hashes(item):
            byte_idx = pos // 8
            bit_idx = pos % 8
            if not (self.bit_array[byte_idx] & (1 << bit_idx)):
                return False
        return True
    
    def __len__(self) -> int:
        return self.count


# =============================================================================
# PHISHING DETECTOR CLASS
# =============================================================================
class PhishingDetector:
    """
    High-performance phishing URL detector.
    Supports both Redis Bloom Filter and in-memory fallback.
    
    Bloom Filter Properties:
    - O(1) lookup time regardless of dataset size
    - Memory efficient: ~1.2 bytes per URL at 0.1% false positive rate
    - No false negatives: if URL is in the set, it will ALWAYS be detected
    - Possible false positives: ~0.1% chance of flagging a safe URL as dangerous
    """
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.bloom_filter_name = BLOOM_FILTER_NAME
        self._url_count = 0
        self.use_redis = redis_client is not None
        
        # In-memory fallback
        self.memory_filter: Optional[InMemoryBloomFilter] = None
        
        if not self.use_redis:
            logger.info("Using in-memory Bloom Filter (Redis not available)")
            self.memory_filter = InMemoryBloomFilter(
                BLOOM_FILTER_CAPACITY, 
                BLOOM_FILTER_ERROR_RATE
            )
    
    async def initialize_bloom_filter(self) -> None:
        """Create Bloom Filter if it doesn't exist"""
        if not self.use_redis:
            logger.info("In-memory Bloom Filter ready")
            return
        
        try:
            # Check if Bloom Filter already exists
            exists = self.redis.exists(self.bloom_filter_name)
            if not exists:
                # Create new Bloom Filter with specified capacity and error rate
                self.redis.execute_command(
                    "BF.RESERVE",
                    self.bloom_filter_name,
                    BLOOM_FILTER_ERROR_RATE,
                    BLOOM_FILTER_CAPACITY,
                    "NONSCALING"
                )
                logger.info(
                    f"Created Bloom Filter '{self.bloom_filter_name}' "
                    f"(capacity={BLOOM_FILTER_CAPACITY:,}, error_rate={BLOOM_FILTER_ERROR_RATE})"
                )
            else:
                logger.info(f"Bloom Filter '{self.bloom_filter_name}' already exists")
        except Exception as e:
            if "item exists" in str(e).lower():
                logger.info(f"Bloom Filter '{self.bloom_filter_name}' already exists")
            else:
                raise
    
    async def load_urlhaus_dataset(self) -> int:
        """
        Fetch and load URLHaus malicious URLs into Bloom Filter.
        Uses vectorized batch processing for efficiency.
        """
        logger.info("Fetching URLHaus dataset...")
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.get(URLHAUS_CSV_URL)
                response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch URLHaus dataset: {e}")
            raise
        
        # Parse CSV content
        content = response.text
        lines = content.split('\n')
        
        # Skip comment lines (start with #)
        data_lines = [line for line in lines if line and not line.startswith('#')]
        
        if not data_lines:
            logger.warning("No data found in URLHaus dataset")
            return 0
        
        # Parse CSV
        csv_reader = csv.reader(io.StringIO('\n'.join(data_lines)))
        
        urls_to_add = []
        batch_size = 1000
        total_added = 0
        
        for row in csv_reader:
            # URLHaus CSV format: id, dateadded, url, url_status, threat, tags, urlhaus_link, reporter
            if len(row) >= 3:
                url = row[2].strip().strip('"')
                if url:
                    # Normalize URL
                    normalized = self._normalize_url(url)
                    urls_to_add.append(normalized)
                    
                    # Also add just the domain for broader matching
                    domain = self._extract_domain(url)
                    if domain:
                        urls_to_add.append(domain)
        
        logger.info(f"Loading {len(urls_to_add):,} URLs into Bloom Filter (batch size: {batch_size})...")
        
        if self.use_redis:
            # Redis batch insertion
            for i in range(0, len(urls_to_add), batch_size):
                batch = urls_to_add[i:i + batch_size]
                try:
                    self.redis.execute_command("BF.MADD", self.bloom_filter_name, *batch)
                    total_added += len(batch)
                    
                    if total_added % 10000 == 0:
                        logger.info(f"Progress: {total_added:,} URLs loaded...")
                except Exception as e:
                    logger.warning(f"Batch insert warning: {e}")
                    for url in batch:
                        try:
                            self.redis.execute_command("BF.ADD", self.bloom_filter_name, url)
                            total_added += 1
                        except Exception:
                            pass
        else:
            # In-memory batch insertion
            for i in range(0, len(urls_to_add), batch_size):
                batch = urls_to_add[i:i + batch_size]
                total_added += self.memory_filter.add_bulk(batch)
                
                if total_added % 10000 == 0:
                    logger.info(f"Progress: {total_added:,} URLs loaded...")
        
        self._url_count = total_added
        logger.info(f"Successfully loaded {total_added:,} URLs into Bloom Filter")
        return total_added
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for consistent matching"""
        url = url.lower().strip()
        for prefix in ['https://', 'http://', 'ftp://']:
            if url.startswith(prefix):
                url = url[len(prefix):]
                break
        if url.startswith('www.'):
            url = url[4:]
        url = url.rstrip('/')
        return url
    
    def _extract_domain(self, url: str) -> Optional[str]:
        """Extract domain from URL"""
        try:
            normalized = self._normalize_url(url)
            domain = normalized.split('/')[0]
            return domain if domain else None
        except Exception:
            return None
    
    def check_url(self, url: str) -> TrustCheckResponse:
        """Check if URL is potentially malicious"""
        if not url:
            raise ValueError("URL cannot be empty")
        
        normalized = self._normalize_url(url)
        domain = self._extract_domain(url)
        
        if self.use_redis:
            url_in_filter = self.redis.execute_command("BF.EXISTS", self.bloom_filter_name, normalized)
            domain_in_filter = False
            if domain:
                domain_in_filter = self.redis.execute_command("BF.EXISTS", self.bloom_filter_name, domain)
        else:
            url_in_filter = self.memory_filter.exists(normalized)
            domain_in_filter = self.memory_filter.exists(domain) if domain else False
        
        if url_in_filter or domain_in_filter:
            confidence = 0.95 if url_in_filter else 0.75
            return TrustCheckResponse(
                status="danger",
                confidence=confidence,
                url=url,
                domain=domain,
                message="⚠️ URL found in known malicious database (URLHaus)"
            )
        else:
            return TrustCheckResponse(
                status="safe",
                confidence=0.85,
                url=url,
                domain=domain,
                message="✓ URL not found in known threat databases"
            )
    
    @property
    def url_count(self) -> int:
        return self._url_count
    
    @property
    def mode(self) -> str:
        return "redis" if self.use_redis else "in-memory"


# =============================================================================
# IMAGE DEEPFAKE DETECTOR
# =============================================================================



# =============================================================================
# GLOBAL STATE
# =============================================================================
redis_client = None
phishing_detector: Optional[PhishingDetector] = None
deepfake_detector: Optional[ImageDeepfakeDetector] = None


# =============================================================================
# APPLICATION LIFECYCLE
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global redis_client, phishing_detector, deepfake_detector
    
    logger.info("=" * 60)
    logger.info("TrustSentinel Backend Starting...")
    logger.info("=" * 60)
    
    # Try to connect to Redis
    redis_connected = False
    if REDIS_AVAILABLE:
        try:
            redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                decode_responses=True,
                socket_connect_timeout=5
            )
            redis_client.ping()
            redis_connected = True
            logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        except Exception as e:
            logger.warning(f"Redis not available: {e}")
            logger.info("Falling back to in-memory Bloom Filter")
            redis_client = None
    else:
        logger.info("Redis module not installed, using in-memory Bloom Filter")
    
    # Initialize PhishingDetector
    phishing_detector = PhishingDetector(redis_client if redis_connected else None)
    
    # Initialize Bloom Filter
    await phishing_detector.initialize_bloom_filter()
    
    # Load URLHaus dataset
    try:
        await phishing_detector.load_urlhaus_dataset()
    except Exception as e:
        logger.error(f"Failed to load URLHaus dataset: {e}")
        logger.warning("Starting with empty Bloom Filter")
    
    # Initialize DeepfakeDetector with model if exists
    deepfake_detector = ImageDeepfakeDetector(model_path="deepfake_model.pkl")
    
    logger.info("=" * 60)
    logger.info(f"TrustSentinel Backend Ready! (Mode: {phishing_detector.mode})")
    logger.info("Deepfake detection endpoint available at /detect-deepfake")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("Shutting down TrustSentinel Backend...")
    if redis_client:
        redis_client.close()


# =============================================================================
# FASTAPI APPLICATION
# =============================================================================
app = FastAPI(
    title="TrustSentinel API",
    description="High-speed phishing URL detection using Bloom Filters",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for hackathon demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# API ENDPOINTS
# =============================================================================
@app.get("/check-trust", response_model=TrustCheckResponse)
async def check_url_trust(
    url: str = Query(..., description="URL to check for phishing/malware")
):
    """Check if a URL is potentially malicious"""
    if not phishing_detector:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        result = phishing_detector.check_url(url)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error checking URL: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    redis_connected = False
    bloom_size = 0
    mode = "unknown"
    
    if phishing_detector:
        bloom_size = phishing_detector.url_count
        mode = phishing_detector.mode
        redis_connected = phishing_detector.use_redis
    
    if redis_client and redis_connected:
        try:
            redis_client.ping()
        except Exception:
            redis_connected = False
    
    return HealthResponse(
        status="healthy",
        redis_connected=redis_connected,
        bloom_filter_size=bloom_size,
        message=f"TrustSentinel API is operational ({mode} mode)",
        mode=mode
    )


@app.post("/detect-deepfake", response_model=DeepfakeCheckResponse)
async def detect_deepfake(image: UploadFile = File(...)):
    """
    Analyze an uploaded image for deepfake indicators.
    
    Accepts: JPEG, PNG, WebP images
    Returns: Deepfake probability score (0-100%) with analysis details
    """
    if not deepfake_detector:
        raise HTTPException(status_code=503, detail="Deepfake detector not initialized")
    
    # Validate content type
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/jpg"]
    if image.content_type and image.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )
    
    try:
        # Read image bytes
        image_bytes = await image.read()
        
        if len(image_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        
        if len(image_bytes) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=400, detail="File too large. Maximum 10MB")
        
        # Analyze image
        result = deepfake_detector.analyze_image(image_bytes, filename=image.filename)
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing image: {e}")
        raise HTTPException(status_code=500, detail="Error processing image")


# =============================================================================
# STATIC FILE SERVING (PRODUCTION)
# =============================================================================
# Mount static files from React build
# Use abspath to ensure we get the correct structure regardless of how script is run
current_dir = os.path.dirname(os.path.abspath(__file__))
dist_path = os.path.join(os.path.dirname(current_dir), "app", "dist")

# Debug log
logger.info(f"Checking for frontend build at: {dist_path}")

if os.path.exists(dist_path):
    app.mount("/assets", StaticFiles(directory=os.path.join(dist_path, "assets")), name="assets")
    
    @app.get("/")
    async def serve_spa_root():
        """Serve the React App root"""
        return FileResponse(os.path.join(dist_path, "index.html"))

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # API routes are already handled above because they are defined first.
        # This catch-all serves index.html for unknown routes to let React Router handle them.
        
        # Check if file exists in dist (e.g. favicon.ico, manifest.json)
        file_path = os.path.join(dist_path, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
             return FileResponse(file_path)
             
        # Otherwise return index.html
        return FileResponse(os.path.join(dist_path, "index.html"))
    
    logger.info(f"Serving static frontend from {dist_path}")
else:
    logger.warning(f"Frontend build not found at {dist_path}. Run 'npm run build' in app/ directory.")

    @app.get("/")
    async def root():
        """Root endpoint with API info (Dev Mode - Frontend Missing)"""
        return {
            "error": "Frontend build not found",
            "path_checked": dist_path,
            "name": "TrustSentinel API",
            "version": "1.1.0",
            "mode": phishing_detector.mode if phishing_detector else "initializing",
        }


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================
@app.post("/detect-deepfake-video", response_model=DeepfakeCheckResponse)
async def detect_deepfake_video(
    video: UploadFile = File(..., description="Video file to analyze")
):
    if not deepfake_detector:
        raise HTTPException(status_code=503, detail="Deepfake detection service not initialized")
    
    # Save uploaded video to temporary file
    tmp_video_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
            shutil.copyfileobj(video.file, tmp_video)
            tmp_video_path = tmp_video.name
            
        logger.info(f"Analyzing video: {tmp_video_path}")
        result = deepfake_detector.analyze_video(tmp_video_path)
        
        # Cleanup
        os.unlink(tmp_video_path)
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing deepfake video: {e}")
        # Ensure cleanup on error
        if tmp_video_path and os.path.exists(tmp_video_path):
            os.unlink(tmp_video_path)
        raise HTTPException(status_code=500, detail=f"Internal server error during video analysis: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
