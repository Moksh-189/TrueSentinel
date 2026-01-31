
import logging
import cv2
import numpy as np
from scipy import fft as scipy_fft
from typing import Tuple, Optional, Any
from pydantic import BaseModel
import pickle
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Try to import PyTorch
TORCH_AVAILABLE = False
try:
    import torch
    import torch.nn as nn
    from torchvision.models.video import resnext50_32x4d, ResNeXt50_32X4D_Weights
    from torchvision import models
    from torchvision import transforms
    TORCH_AVAILABLE = True
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"PyTorch available. Using device: {DEVICE}")
except ImportError:
    torch = None
    nn = None
    DEVICE = None
    logger.warning("PyTorch not available. ResNext+LSTM model will not work.")

# Try to import mediapipe
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    mp = None


# =============================================================================
# ResNext + LSTM Model Architecture (for inference)
# =============================================================================

if TORCH_AVAILABLE:
    class ResNextLSTMPretrained(nn.Module):
        """
        ResNext + LSTM model matching the GitHub pretrained model structure.
        This matches the state_dict keys: model.X, lstm, linear1
        """
        
        def __init__(self, num_classes=2):
            super(ResNextLSTMPretrained, self).__init__()
            
            # Load pretrained ResNext50 and extract backbone (without FC)
            resnext = resnext50_32x4d(weights=None)  # Don't load ImageNet weights
            
            # Create Sequential model matching pretrained structure
            # The pretrained model uses model.0 through model.7 (ResNext layers without FC)
            self.model = nn.Sequential(
                resnext.conv1,      # model.0
                resnext.bn1,        # model.1
                resnext.relu,       # model.2
                resnext.maxpool,    # model.3
                resnext.layer1,     # model.4
                resnext.layer2,     # model.5
                resnext.layer3,     # model.6
                resnext.layer4,     # model.7
            )
            
            # LSTM for temporal modeling (single layer, unidirectional, no bias based on pretrained keys)
            self.lstm = nn.LSTM(
                input_size=2048,  # ResNext50 output features
                hidden_size=2048,
                num_layers=1,
                batch_first=True,
                bidirectional=False,
                bias=False  # Pretrained model has no bias in LSTM
            )
            
            # Linear classification head
            self.linear1 = nn.Linear(2048, num_classes)
            
            # Pooling for feature extraction
            self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        
        def forward(self, x):
            """
            Forward pass for video sequences.
            x: (batch, seq_len, C, H, W)
            """
            batch_size, seq_len, C, H, W = x.shape
            
            # Process each frame through CNN
            x = x.view(batch_size * seq_len, C, H, W)
            features = self.model(x)
            features = self.avgpool(features)
            features = features.view(batch_size, seq_len, -1)
            
            # LSTM temporal processing
            lstm_out, _ = self.lstm(features)
            
            # Use last timestep for classification
            last_output = lstm_out[:, -1, :]
            
            # Classification
            logits = self.linear1(last_output)
            return logits
        
        def predict_single_image(self, image_tensor):
            """Predict on a single image (adds sequence dimension)."""
            if image_tensor.dim() == 3:
                image_tensor = image_tensor.unsqueeze(0)  # Add batch dim
            if image_tensor.dim() == 4:
                image_tensor = image_tensor.unsqueeze(1)  # Add sequence dim
            return self.forward(image_tensor)


class DeepfakeCheckResponse(BaseModel):
    """Response model for deepfake detection"""
    status: str  # "authentic" or "suspicious"
    deepfake_score: float  # 0-100 percentage
    confidence: str  # "low", "medium", "high"
    face_detected: bool
    analysis_details: dict
    message: str

class ImageDeepfakeDetector:
    """
    Image-based deepfake detector using ensemble analysis.
    
    Uses multiple signals to detect potential image manipulation:
    1. Face artifact analysis - Detects unnatural edges around face regions
    2. Color statistics - Analyzes RGB/HSV distributions for anomalies
    3. Frequency analysis - DCT to detect GAN fingerprints
    4. Texture consistency - Laplacian variance for blur detection
    """
    
    def __init__(self, model_path: Optional[str] = None):
        # Initialize MediaPipe Face Mesh if available
        self.face_mesh = None
        if MEDIAPIPE_AVAILABLE and mp is not None:
            try:
                self.mp_face_mesh = mp.solutions.face_mesh
                self.face_mesh = self.mp_face_mesh.FaceMesh(
                    static_image_mode=True,
                    max_num_faces=1,
                    refine_landmarks=True,
                    min_detection_confidence=0.5
                )
                logger.info("ImageDeepfakeDetector initialized with MediaPipe")
            except Exception as e:
                logger.warning(f"MediaPipe initialization failed: {e}")
                self.face_mesh = None
        else:
            logger.info("ImageDeepfakeDetector initialized without MediaPipe (face detection disabled)")
            
        # Initialize OpenCV Haar Cascade as fallback
        try:
            face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(face_cascade_path)
            logger.info("OpenCV Haar Cascade initialized as fallback")
        except Exception as e:
            logger.warning(f"Failed to initialize Haar Cascade: {e}")
            self.face_cascade = None
            
        # Initialize models
        self.model = None  # sklearn model (pickle)
        self.torch_model = None  # PyTorch ResNext+LSTM model
        self.torch_transform = None  # Image preprocessing for PyTorch
        
        # Try to load PyTorch pretrained model first
        # Priority 0: DenseNet121 (Project 140k dataset)
        densenet_path = os.path.join(os.path.dirname(__file__), 'deepfake_model_densenet.pt')
        # Priority 1: ResNext+LSTM (High Accuracy Model)
        pretrained_path = os.path.join(os.path.dirname(__file__), 'deepfake_model_pretrained.pt')
        
        logger.info(f"Checking for models...")
        logger.info(f" - DenseNet path: {densenet_path} (Exists: {os.path.exists(densenet_path)})")
        logger.info(f" - ResNext path: {pretrained_path} (Exists: {os.path.exists(pretrained_path)})")

        if TORCH_AVAILABLE:
            try:
                if os.path.exists(densenet_path):
                    # Load DenseNet121
                    self.torch_model = models.densenet121(weights=None)
                    num_ftrs = self.torch_model.classifier.in_features
                    self.torch_model.classifier = nn.Sequential(
                        nn.Linear(num_ftrs, 512),
                        nn.ReLU(),
                        nn.Dropout(0.3),
                        nn.Linear(512, 2)
                    )
                    state_dict = torch.load(densenet_path, map_location=DEVICE)
                    self.torch_model.load_state_dict(state_dict)
                    self.model_type = "densenet"
                    logger.info(f"SUCCESS: Loaded DenseNet121 model from {densenet_path}")
                elif os.path.exists(pretrained_path):
                    self.torch_model = ResNextLSTMPretrained(num_classes=2)
                    state_dict = torch.load(pretrained_path, map_location=DEVICE)
                    self.torch_model.load_state_dict(state_dict)
                    self.model_type = "resnext_lstm"
                    logger.info(f"SUCCESS: Loaded pretrained ResNext+LSTM model from {pretrained_path}")
                else:
                    logger.warning("No PyTorch model files found ('deepfake_model_densenet.pt' or 'deepfake_model_pretrained.pt')")
                
                if self.torch_model:
                    self.torch_model.to(DEVICE)
                    self.torch_model.eval()
                    # Setup image preprocessing
                    self.torch_transform = transforms.Compose([
                        transforms.ToPILImage(),
                        transforms.Resize((224, 224)),
                        transforms.ToTensor(),
                        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
                    ])
            except Exception as e:
                logger.error(f"CRITICAL: Failed to load PyTorch model: {e}", exc_info=True)
                self.torch_model = None

    def _process_frame(self, image: np.ndarray) -> DeepfakeCheckResponse:
        # Detect face
        face_landmarks, face_rect = self.detect_face(image)
        
        # ... (rest of feature extraction) ...
        # (Assuming extract_features is unchanged)
        features = self.extract_features(image, face_landmarks, face_rect)
        
        # Extract individual scores for heuristic fallback
        artifact_score = features['artifact_score']
        color_score = features['color_score']
        frequency_score = features['frequency_score']
        texture_score = features['texture_score']
        
        # Use trained model if available
        deepfake_score = 0.0
        model_used = "heuristic"
        
        # Priority 1: PyTorch Model
        if self.torch_model is not None and TORCH_AVAILABLE:
            try:
                # Preprocess image for PyTorch
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                img_tensor = self.torch_transform(rgb_image)
                
                with torch.no_grad():
                    if getattr(self, 'model_type', '') == 'densenet':
                        # DenseNet takes [1, 3, 224, 224]
                        img_tensor = img_tensor.unsqueeze(0).to(DEVICE)
                        outputs = self.torch_model(img_tensor)
                        probs = torch.softmax(outputs, dim=1)
                        # DenseNet training: 0=Fake, 1=Real (based on ImageFolder default alphabetical: fake, real)
                        # So Deepfake score is Class 0
                        deepfake_score = probs[0, 0].item() * 100
                        model_used = "DenseNet121"
                    else:
                        # ResNext+LSTM takes [1, 1, 3, 224, 224]
                        img_tensor = img_tensor.unsqueeze(0).unsqueeze(0).to(DEVICE)
                        outputs = self.torch_model(img_tensor)
                        probs = torch.softmax(outputs, dim=1)
                        # Check if classes are inverted (common in ImageFolder: fake < real alphabetically)
                        fake_prob = probs[0, 0].item() 
                        deepfake_score = fake_prob * 100
                        model_used = "ResNext+LSTM"
                        
            except Exception as e:
                logger.warning(f"PyTorch inference failed: {e}")
                deepfake_score = 0.0
        
        # Fallback: Load sklearn pickle model
        if self.torch_model is None and model_path and os.path.exists(model_path):
            try:
                with open(model_path, 'rb') as f:
                    self.model = pickle.load(f)
                logger.info(f"Loaded sklearn model from {model_path}")
            except Exception as e:
                logger.error(f"Failed to load sklearn model from {model_path}: {e}")

    def detect_face(self, image: np.ndarray) -> Tuple[Any, Any]:
        """Detect face using MediaPipe or Haar Cascade with Center Crop Fallback"""
        face_landmarks = None
        face_rect = None
        
        # Try MediaPipe first
        if self.face_mesh:
            try:
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                results = self.face_mesh.process(rgb_image)
                if results.multi_face_landmarks:
                    face_landmarks = results.multi_face_landmarks[0]
            except Exception as e:
                pass
        
        # Fallback to Haar Cascade
        if face_landmarks is None and self.face_cascade:
            try:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
                if len(faces) > 0:
                    # Get largest face
                    face_rect = max(faces, key=lambda r: r[2] * r[3])
            except Exception:
                pass
        
        # Final Fallback: Center Crop (treat center of image as face area)
        if face_landmarks is None and face_rect is None:
            h, w = image.shape[:2]
            # Take center 50% of image
            cx, cy = w // 2, h // 2
            cw, ch = w // 2, h // 2
            face_rect = (cx - cw//2, cy - ch//2, cw, ch)
            
        return face_landmarks, face_rect

    def extract_features(self, image: np.ndarray, face_landmarks=None, face_rect=None) -> dict:
        """Extract all features for a face image. Requires either face_landmarks or face_rect."""
        artifact_score = self._analyze_artifacts(image, face_landmarks, face_rect)
        color_score = self._analyze_color_statistics(image, face_landmarks, face_rect)
        frequency_score = self._analyze_frequency_domain(image)
        texture_score = self._analyze_texture_consistency(image, face_landmarks, face_rect)
        
        return {
            'artifact_score': artifact_score,
            'color_score': color_score,
            'frequency_score': frequency_score,
            'texture_score': texture_score
        }
    
    def analyze_image(self, image_bytes: bytes, filename: str = None) -> DeepfakeCheckResponse:
        # Decode image
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return DeepfakeCheckResponse(
                status="error",
                deepfake_score=0.0,
                confidence="low",
                face_detected=False,
                analysis_details={},
                message="Could not decode image"
            )
            
        # Process frame
        result = self._process_frame(image)
        
        return result

    def analyze_video(self, video_path: str) -> DeepfakeCheckResponse:
        """Analyze a video file by processing sampled frames."""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return DeepfakeCheckResponse(
                    status="error", deepfake_score=0.0, confidence="low", 
                    face_detected=False, analysis_details={}, message="Could not open video file"
                )
            
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frames_to_extract = 20
            
            if total_frames <= 0:
                 # Fallback if frame count extraction fails
                 total_frames = 100 
            
            # Sample frames uniformly
            indices = sorted(list(set(np.linspace(0, total_frames - 1, frames_to_extract).astype(int))))
            
            frame_scores = []
            faces_detected = 0
            
            for idx in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if ret:
                    # Process frame
                    result = self._process_frame(frame)
                    if result.face_detected:
                        faces_detected += 1
                        frame_scores.append(result.deepfake_score)
            
            cap.release()
            
            if not frame_scores:
                return DeepfakeCheckResponse(
                    status="authentic", deepfake_score=0.0, confidence="low",
                    face_detected=False, analysis_details={}, 
                    message="No faces detected in video frames"
                )
            
            avg_score = sum(frame_scores) / len(frame_scores)
            
            # Apply same bias toward authentic as images
            avg_score = avg_score * 0.8
            
            # Log the score for debugging
            logger.info(f"Video Analysis Result - Avg Score: {avg_score:.2f}% (Threshold: 85%)")
            
            # Very strict threshold to prevent false positives
            status = "suspicious" if avg_score > 85 else "authentic"
            confidence = "high" if faces_detected > 5 and (avg_score > 90 or avg_score < 15) else "medium"
            
            msg = f"✓ Video appears authentic (Score: {avg_score:.1f}%)"
            if status == "suspicious":
                msg = f"⚠️ Possible deepfake detected (Score: {avg_score:.1f}%)"
            
            return DeepfakeCheckResponse(
                status=status,
                deepfake_score=avg_score,
                confidence=confidence,
                face_detected=True,
                analysis_details={"frames_analyzed": len(frame_scores), "faces_found": faces_detected},
                message=msg
            )
            
        except Exception as e:
            logger.error(f"Video analysis failed: {e}")
            return DeepfakeCheckResponse(
                status="error", deepfake_score=0.0, confidence="low",
                face_detected=False, analysis_details={}, message=str(e)
            )

    def _process_frame(self, image: np.ndarray) -> DeepfakeCheckResponse:
        """Internal method to process a single loaded opencv image"""
        try:
            # Convert to RGB for MediaPipe
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Check if face detector is initialized
            if self.face_mesh is None and self.face_cascade is None:
                return DeepfakeCheckResponse(
                    status="error", deepfake_score=0.0, confidence="low",
                    face_detected=False, analysis_details={},
                    message="❌ Deepfake detection unavailable (No face detector)"
                )
    
            # Detect face
            face_landmarks = None
            
            # Try MediaPipe first
            if self.face_mesh:
                try:
                    results = self.face_mesh.process(rgb_image)
                    if results.multi_face_landmarks:
                        face_landmarks = results.multi_face_landmarks[0]
                except Exception:
                    pass
            
            # Fallback to Haar Cascade
            face_rect = None
            if face_landmarks is None and self.face_cascade:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
                if len(faces) > 0:
                    face_rect = max(faces, key=lambda r: r[2] * r[3])
            
            if not face_landmarks and face_rect is None:
                return DeepfakeCheckResponse(
                    status="unknown", deepfake_score=0.0, confidence="low",
                    face_detected=False, analysis_details={},
                    message="⚠️ No face detected"
                )
            
            # Extract features
            features = self.extract_features(image, face_landmarks, face_rect)
            
            artifact_score = features['artifact_score']
            color_score = features['color_score']
            frequency_score = features['frequency_score']
            texture_score = features['texture_score']
            
            # Use trained model if available
            deepfake_score = 0.0
            model_used = "heuristic"
            
            # Priority 1: PyTorch ResNext+LSTM model
            if self.torch_model is not None and TORCH_AVAILABLE:
                try:
                    # Preprocess image for PyTorch
                    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    img_tensor = self.torch_transform(rgb_image)
                    
                    # Add batch and sequence dimensions
                    img_tensor = img_tensor.unsqueeze(0).unsqueeze(0).to(DEVICE)
                    
                    with torch.no_grad():
                        outputs = self.torch_model(img_tensor)
                        probs = torch.softmax(outputs, dim=1)
                        # Check if classes are inverted (common in ImageFolder: fake < real alphabetically)
                        # Assuming Class 0 = Fake, Class 1 = Real
                        fake_prob = probs[0, 0].item() 
                        raw_score = fake_prob * 100
                        deepfake_score = raw_score
                    model_used = "ResNext+LSTM"
                except Exception as e:
                    logger.warning(f"PyTorch inference failed: {e}")
                    deepfake_score = 0.0
            
            # Priority 2: sklearn pickle model
            if deepfake_score == 0.0 and self.model:
                try:
                    feature_vector = np.array([[
                        artifact_score, color_score, frequency_score, texture_score
                    ]])
                    probs = self.model.predict_proba(feature_vector)[0]
                    raw_score = probs[1] * 100
                    deepfake_score = max(0, raw_score * 0.8)
                    model_used = "RandomForest"
                except Exception:
                    deepfake_score = self._heuristic_score(artifact_score, color_score, frequency_score, texture_score)
            
            # Priority 3: Heuristic fallback
            if deepfake_score == 0.0:
                deepfake_score = self._heuristic_score(artifact_score, color_score, frequency_score, texture_score)
            
            # Determine confidence
            scores = [artifact_score, color_score, frequency_score, texture_score]
            score_variance = np.std(scores)
            confidence = "high" if score_variance < 10 else ("medium" if score_variance < 20 else "low")
            
            # Determine status
            status = "authentic"
            message = "✓ Authentic - No manipulation detected"
            
            # Binary threshold as requested: 
            # If Authentic score < 50% (i.e. Deepfake score >= 50%), then it's Fake.
            if deepfake_score >= 50:
                status = "suspicious"
                message = "⚠️ Deepfake detected"
            
            return DeepfakeCheckResponse(
                status=status,
                deepfake_score=round(deepfake_score, 1),
                confidence=confidence,
                face_detected=True,
                analysis_details={
                    "artifact_score": round(artifact_score, 1),
                    "color_score": round(color_score, 1),
                    "frequency_score": round(frequency_score, 1),
                    "texture_score": round(texture_score, 1)
                },
                message=message
            )
        except Exception as e:
            logger.error(f"Error in _process_frame: {e}")
            return DeepfakeCheckResponse(
                status="error", deepfake_score=0.0, confidence="low",
                face_detected=False, analysis_details={}, message=str(e)
            )

    def _heuristic_score(self, artifact, color, freq, texture):
        # Weighted ensemble score
        weights = {
            'artifact': 0.25,
            'color': 0.25,
            'frequency': 0.30,
            'texture': 0.20
        }
        
        return (
            artifact * weights['artifact'] +
            color * weights['color'] +
            freq * weights['frequency'] +
            texture * weights['texture']
        )
    
    def _get_face_roi(self, image: np.ndarray, face_landmarks=None, face_rect=None) -> Tuple[np.ndarray, tuple]:
        """Extract face region of interest"""
        h, w = image.shape[:2]
        
        if face_landmarks:
            xs = [int(lm.x * w) for lm in face_landmarks.landmark]
            ys = [int(lm.y * h) for lm in face_landmarks.landmark]
            
            x_min = max(0, min(xs) - 20)
            x_max = min(w, max(xs) + 20)
            y_min = max(0, min(ys) - 20)
            y_max = min(h, max(ys) + 20)
        elif face_rect is not None:
            x, y, fw, fh = face_rect
            x_min = max(0, x - 20)
            x_max = min(w, x + fw + 20)
            y_min = max(0, y - 20)
            y_max = min(h, y + fh + 20)
        else:
            return np.array([]), (0,0,0,0)
        
        roi = image[y_min:y_max, x_min:x_max]
        return roi, (x_min, y_min, x_max, y_max)
    
    def _analyze_artifacts(self, image: np.ndarray, face_landmarks=None, face_rect=None) -> float:
        """
        Analyze face boundary for artifacts.
        """
        try:
            roi, _ = self._get_face_roi(image, face_landmarks, face_rect)
            if roi.size == 0:
                return 50.0
            
            # Convert to grayscale
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            
            # Detect edges using Canny
            edges = cv2.Canny(gray, 50, 150)
            
            # Analyze edge distribution at boundaries
            h, w = edges.shape
            border_width = max(5, min(h, w) // 10)
            
            # Extract border regions
            top = edges[:border_width, :]
            bottom = edges[-border_width:, :]
            left = edges[:, :border_width]
            right = edges[:, -border_width:]
            
            # Calculate edge intensity at borders vs center
            border_intensity = np.mean([
                np.mean(top), np.mean(bottom),
                np.mean(left), np.mean(right)
            ])
            
            center = edges[border_width:-border_width, border_width:-border_width]
            center_intensity = np.mean(center) if center.size > 0 else 0
            
            # High border intensity relative to center suggests artifacts
            if center_intensity > 0:
                ratio = border_intensity / (center_intensity + 1e-10)
                # Reduced multiplier to be less aggressive
                score = min(100, ratio * 30)
            else:
                score = 10.0 # Lower base score for clean images
            
            return score
        except Exception as e:
            logger.warning(f"Artifact analysis error: {e}")
            return 50.0
    
    def _analyze_color_statistics(self, image: np.ndarray, face_landmarks=None, face_rect=None) -> float:
        """
        Analyze color distribution for anomalies.
        """
        try:
            roi, _ = self._get_face_roi(image, face_landmarks, face_rect)
            if roi.size == 0:
                return 50.0
            
            # Convert to HSV
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            
            # Analyze saturation channel
            saturation = hsv[:, :, 1]
            sat_std = np.std(saturation)
            
            # Very uniform or very varied saturation is suspicious
            if sat_std < 10 or sat_std > 70: # Widened acceptable range
                sat_score = 60
            elif sat_std < 20 or sat_std > 60:
                sat_score = 40
            else:
                sat_score = 10 # Lower base score
            
            # Analyze color channel correlation
            b, g, r = cv2.split(roi)
            
            # Calculate correlation between channels
            rg_corr = np.corrcoef(r.flatten(), g.flatten())[0, 1]
            gb_corr = np.corrcoef(g.flatten(), b.flatten())[0, 1]
            
            # Natural skin has high channel correlation
            avg_corr = (abs(rg_corr) + abs(gb_corr)) / 2
            
            if avg_corr > 0.92:
                corr_score = 10  # Very natural
            elif avg_corr > 0.8:
                corr_score = 30
            else:
                corr_score = 60  # Suspicious
            
            return (sat_score + corr_score) / 2
        except Exception as e:
            logger.warning(f"Color analysis error: {e}")
            return 50.0
    
    def _analyze_frequency_domain(self, image: np.ndarray) -> float:
        """
        Analyze frequency domain for GAN fingerprints.
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Resize to standard size for consistent analysis
            gray = cv2.resize(gray, (256, 256))
            
            # Apply DCT
            dct = cv2.dct(np.float32(gray))
            
            # Analyze high-frequency components
            h, w = dct.shape
            
            # Divide into frequency bands
            mid_freq = dct[h//4:h//2, w//4:w//2]
            high_freq = dct[h//2:, w//2:]
            
            # Calculate energy in each band
            # low_energy = np.sum(np.abs(low_freq))
            mid_energy = np.sum(np.abs(mid_freq))
            high_energy = np.sum(np.abs(high_freq))
            
            total_energy = np.sum(np.abs(dct)) + 1e-10
            
            # Ratio of high to mid frequency energy
            high_ratio = high_energy / total_energy
            
            # Analyze periodicity in high frequencies (GAN artifacts)
            high_freq_1d = dct[h//2:, w//2:].flatten()
            
            if len(high_freq_1d) > 10:
                # Calculate spectral flatness
                geometric_mean = np.exp(np.mean(np.log(np.abs(high_freq_1d) + 1e-10)))
                arithmetic_mean = np.mean(np.abs(high_freq_1d)) + 1e-10
                spectral_flatness = geometric_mean / arithmetic_mean
                
                # High spectral flatness suggests artificial noise patterns
                if spectral_flatness > 0.6: # Raised threshold
                    freq_score = 60
                elif spectral_flatness > 0.4:
                    freq_score = 40
                else:
                    freq_score = 10 # Lower base score
            else:
                freq_score = 30
            
            # Combine with energy ratio analysis
            if high_ratio > 0.2: # Raised threshold
                ratio_score = 60
            elif high_ratio > 0.12:
                ratio_score = 40
            else:
                ratio_score = 10
            
            return (freq_score + ratio_score) / 2
        except Exception as e:
            logger.warning(f"Frequency analysis error: {e}")
            return 50.0
    
    def _analyze_texture_consistency(self, image: np.ndarray, face_landmarks=None, face_rect=None) -> float:
        """
        Analyze texture consistency across face regions.
        """
        try:
            h, w = image.shape[:2]
            
            # Define regions to analyze (forehead, left cheek, right cheek)
            regions = []
            
            if face_landmarks:
                landmarks = face_landmarks.landmark
                # Forehead region (landmarks around top of face)
                forehead_indices = [10, 67, 109, 108, 69, 104, 68, 338, 337, 336]
                
                for idx in forehead_indices[:5]:
                    lm = landmarks[idx]
                    x, y = int(lm.x * w), int(lm.y * h)
                    if 10 < x < w-10 and 10 < y < h-10:
                        patch = image[y-10:y+10, x-10:x+10]
                        if patch.size > 0:
                            regions.append(patch)
            elif face_rect is not None:
                # With Haar Cascade, assume standard face geometry
                x, y, fw, fh = face_rect
                # Forehead
                fx, fy = x + fw//2, y + fh//4
                patch = image[fy-10:fy+10, fx-10:fx+10]
                if patch.size > 0:
                    regions.append(patch)
                # Cheeks
                lx, ly = x + fw//4, y + fh//2 + fh//8
                patch = image[ly-10:ly+10, lx-10:lx+10]
                if patch.size > 0:
                    regions.append(patch)
                rx, ry = x + 3*fw//4, y + fh//2 + fh//8
                patch = image[ry-10:ry+10, rx-10:rx+10]
                if patch.size > 0:
                    regions.append(patch)
            
            if len(regions) < 2:
                return 50.0
            
            # Calculate Laplacian variance for each region (sharpness measure)
            sharpness_values = []
            for region in regions:
                gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY) if len(region.shape) == 3 else region
                laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
                sharpness_values.append(laplacian_var)
            
            # Calculate consistency (coefficient of variation)
            mean_sharpness = np.mean(sharpness_values)
            std_sharpness = np.std(sharpness_values)
            
            if mean_sharpness > 0:
                cv = std_sharpness / mean_sharpness
            else:
                cv = 0
            
            # High variation suggests inconsistent processing (deepfake)
            if cv > 0.9: # Raised threshold
                score = 70
            elif cv > 0.6:
                score = 50
            elif cv > 0.4:
                score = 30
            else:
                score = 10 # Lower base score
            
            return score
        except Exception as e:
            logger.warning(f"Texture analysis error: {e}")
            return 50.0
