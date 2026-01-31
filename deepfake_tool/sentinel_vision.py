"""
TrustSentinel Bio-Liveness Detector (Deepfake Shield)
======================================================
Standalone script for detecting human liveness using rPPG (Remote Photoplethysmography).

This tool analyzes subtle color variations in facial skin caused by blood flow
to detect a heartbeat signal. Real humans exhibit this signal; deepfakes do not.

THEORY OF OPERATION:
====================
1. Blood absorbs green light more than red or blue
2. With each heartbeat, blood volume in facial capillaries changes slightly
3. This causes micro-variations in skin color (invisible to naked eye)
4. By extracting the green channel mean over time, we get a time-domain signal
5. FFT reveals the dominant frequency, which corresponds to heart rate

TECHNICAL DETAILS:
==================
- Signal source: Green channel mean from forehead and cheeks (high capillary density)
- Buffer size: 150 frames (~5 seconds at 30fps)
- Valid heartbeat range: 0.8 Hz (48 BPM) to 3.0 Hz (180 BPM)
- Detection threshold: Peak magnitude must exceed noise floor by 2x

Author: TrustSentinel Team
"""

import sys
import time
from collections import deque
from typing import Optional, Tuple, List

import cv2
import mediapipe as mp
import numpy as np
from scipy import fft
from scipy.signal import butter, filtfilt

# =============================================================================
# CONFIGURATION
# =============================================================================

# Frame buffer size for FFT analysis
# At 30fps, 150 frames = 5 seconds of data
# Minimum needed to detect frequencies as low as 0.2 Hz (12 BPM)
BUFFER_SIZE = 150

# Valid heart rate range in Hz
# 0.8 Hz = 48 BPM (athletic/resting), 3.0 Hz = 180 BPM (maximum exercise)
MIN_HEART_RATE_HZ = 0.8
MAX_HEART_RATE_HZ = 3.0

# Minimum peak-to-noise ratio for valid detection
# Higher = more strict, fewer false positives but might miss weak signals
PEAK_NOISE_THRESHOLD = 2.0

# Bandpass filter parameters (for pre-processing signal)
LOWCUT_HZ = 0.7     # Filter frequencies below 0.7 Hz (42 BPM)
HIGHCUT_HZ = 3.5    # Filter frequencies above 3.5 Hz (210 BPM)

# UI Colors (BGR format for OpenCV)
COLOR_LIVENESS = (0, 255, 100)    # Green - living human detected
COLOR_DEEPFAKE = (128, 128, 128)  # Grey - no heartbeat signal
COLOR_SCANNING = (255, 200, 0)    # Cyan - still collecting data
COLOR_GRAPH_BG = (30, 30, 30)     # Dark grey for graph background
COLOR_GRAPH_LINE = (0, 255, 100)  # Green for signal line

# MediaPipe Face Mesh landmark indices
# These define regions of interest (ROI) with high capillary density
# Forehead region landmarks
FOREHEAD_LANDMARKS = [10, 67, 109, 108, 69, 104, 68, 338, 337, 336, 299, 297]
# Left cheek region
LEFT_CHEEK_LANDMARKS = [234, 93, 132, 58, 172, 136, 150, 149, 176, 148]
# Right cheek region
RIGHT_CHEEK_LANDMARKS = [454, 323, 361, 288, 397, 365, 379, 378, 400, 377]


# =============================================================================
# SIGNAL PROCESSING UTILITIES
# =============================================================================

def create_bandpass_filter(lowcut: float, highcut: float, fs: float, order: int = 4):
    """
    Create Butterworth bandpass filter coefficients.
    
    Args:
        lowcut: Low cutoff frequency (Hz)
        highcut: High cutoff frequency (Hz)
        fs: Sampling frequency (fps)
        order: Filter order (higher = sharper cutoff but more ringing)
    
    Returns:
        (b, a) filter coefficients
    """
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    
    # Clamp to valid range (0, 1)
    low = max(0.01, min(low, 0.99))
    high = max(low + 0.01, min(high, 0.99))
    
    b, a = butter(order, [low, high], btype='band')
    return b, a


def apply_bandpass_filter(signal: np.ndarray, b: np.ndarray, a: np.ndarray) -> np.ndarray:
    """
    Apply bandpass filter to signal using zero-phase filtering.
    
    Zero-phase filtering (filtfilt) applies filter forward and backward,
    eliminating phase distortion but requiring the full signal.
    
    Args:
        signal: Input signal array
        b, a: Filter coefficients from create_bandpass_filter
    
    Returns:
        Filtered signal
    """
    # Pad signal to avoid edge effects
    pad_len = 3 * max(len(a), len(b))
    if len(signal) <= pad_len:
        return signal
    
    try:
        filtered = filtfilt(b, a, signal, padlen=pad_len)
        return filtered
    except Exception:
        return signal


def compute_fft_spectrum(signal: np.ndarray, fps: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute FFT and return frequency and magnitude arrays.
    
    MATHEMATICAL EXPLANATION:
    ========================
    The FFT decomposes our time-domain signal into frequency components.
    
    For a signal sampled at fps (frames per second):
    - Maximum detectable frequency = fps / 2 (Nyquist limit)
    - Frequency resolution = fps / N (where N = signal length)
    
    For 150 samples at 30 fps:
    - Nyquist limit = 15 Hz
    - Resolution = 30/150 = 0.2 Hz (can distinguish heart rates 12 BPM apart)
    
    Args:
        signal: Time-domain signal (green channel means over time)
        fps: Sampling rate (frames per second)
    
    Returns:
        (frequencies, magnitudes) - arrays of frequency bins and their magnitudes
    """
    n = len(signal)
    
    # Remove DC component (mean) to focus on oscillations
    signal_centered = signal - np.mean(signal)
    
    # Apply Hann window to reduce spectral leakage
    # Spectral leakage occurs when signal doesn't contain exactly integer
    # number of cycles, causing energy to "leak" to neighboring frequencies
    window = np.hanning(n)
    signal_windowed = signal_centered * window
    
    # Compute real FFT (signal is real, so we only need positive frequencies)
    # rfft is 2x faster than fft for real signals
    fft_result = fft.rfft(signal_windowed)
    
    # Compute magnitude (absolute value of complex FFT result)
    magnitudes = np.abs(fft_result)
    
    # Compute frequency bins
    # rfftfreq returns positive frequencies only
    frequencies = fft.rfftfreq(n, d=1.0/fps)
    
    return frequencies, magnitudes


def find_heart_rate_peak(
    frequencies: np.ndarray,
    magnitudes: np.ndarray,
    min_hz: float = MIN_HEART_RATE_HZ,
    max_hz: float = MAX_HEART_RATE_HZ
) -> Tuple[Optional[float], float, float]:
    """
    Find the dominant frequency peak in the valid heart rate range.
    
    ALGORITHM:
    ==========
    1. Mask frequencies outside valid heart rate range
    2. Find the peak magnitude in the valid range
    3. Calculate noise floor as median of magnitudes outside peak
    4. Return peak frequency if signal-to-noise ratio is sufficient
    
    Args:
        frequencies: Frequency bins from FFT
        magnitudes: Magnitude at each frequency
        min_hz: Minimum valid heart rate frequency
        max_hz: Maximum valid heart rate frequency
    
    Returns:
        (peak_frequency, peak_magnitude, noise_floor)
        peak_frequency is None if no valid peak found
    """
    # Create mask for valid heart rate range
    valid_mask = (frequencies >= min_hz) & (frequencies <= max_hz)
    
    if not np.any(valid_mask):
        return None, 0.0, 0.0
    
    # Extract valid region
    valid_freqs = frequencies[valid_mask]
    valid_mags = magnitudes[valid_mask]
    
    # Find peak in valid region
    peak_idx = np.argmax(valid_mags)
    peak_freq = valid_freqs[peak_idx]
    peak_mag = valid_mags[peak_idx]
    
    # Calculate noise floor (median of magnitudes outside a ±0.3 Hz window around peak)
    noise_mask = np.abs(frequencies - peak_freq) > 0.3
    noise_mask &= valid_mask
    
    if np.any(noise_mask):
        noise_floor = np.median(magnitudes[noise_mask])
    else:
        noise_floor = np.median(valid_mags) * 0.5
    
    return peak_freq, peak_mag, max(noise_floor, 1e-10)


# =============================================================================
# ROI EXTRACTION
# =============================================================================

def extract_roi_polygon(
    frame: np.ndarray,
    landmarks: List,
    indices: List[int]
) -> Optional[np.ndarray]:
    """
    Extract ROI from frame using face mesh landmarks.
    
    Uses vectorized operations for efficiency:
    - Creates polygon mask using cv2.fillPoly
    - Extracts pixels within mask using boolean indexing
    
    Args:
        frame: BGR image frame
        landmarks: MediaPipe face landmarks
        indices: Landmark indices defining the ROI polygon
    
    Returns:
        Array of pixel values within the ROI, or None if invalid
    """
    h, w = frame.shape[:2]
    
    # Convert landmark indices to pixel coordinates
    # Vectorized: process all landmarks at once
    points = []
    for idx in indices:
        lm = landmarks[idx]
        x = int(lm.x * w)
        y = int(lm.y * h)
        if 0 <= x < w and 0 <= y < h:
            points.append([x, y])
    
    if len(points) < 3:
        return None
    
    # Create polygon mask
    points = np.array(points, dtype=np.int32)
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(mask, [points], 255)
    
    # Extract pixels using boolean indexing (vectorized)
    roi_pixels = frame[mask == 255]
    
    return roi_pixels if len(roi_pixels) > 0 else None


def get_green_channel_mean(frame: np.ndarray, face_landmarks) -> Optional[float]:
    """
    Extract mean green channel value from facial ROIs.
    
    WHY GREEN CHANNEL?
    ==================
    Hemoglobin (in blood) has peak absorption in the green wavelength (~550nm).
    When blood volume increases during systole, more green light is absorbed,
    causing slight decrease in green channel value. This creates the strongest
    plethysmographic signal compared to red or blue channels.
    
    We combine forehead + both cheeks for robustness against:
    - Partial occlusion
    - Local lighting variations
    - Motion artifacts
    
    Args:
        frame: BGR image
        face_landmarks: MediaPipe face landmark detection results
    
    Returns:
        Mean green channel value across all ROIs, or None if detection failed
    """
    landmarks = face_landmarks.landmark
    
    # Extract all ROIs
    forehead_pixels = extract_roi_polygon(frame, landmarks, FOREHEAD_LANDMARKS)
    left_cheek_pixels = extract_roi_polygon(frame, landmarks, LEFT_CHEEK_LANDMARKS)
    right_cheek_pixels = extract_roi_polygon(frame, landmarks, RIGHT_CHEEK_LANDMARKS)
    
    # Combine valid ROIs
    all_pixels = []
    for pixels in [forehead_pixels, left_cheek_pixels, right_cheek_pixels]:
        if pixels is not None and len(pixels) > 0:
            all_pixels.append(pixels)
    
    if not all_pixels:
        return None
    
    # Concatenate all ROI pixels (vectorized)
    combined = np.vstack(all_pixels)
    
    # Extract green channel (index 1 in BGR) and compute mean
    # Using NumPy vectorized mean for efficiency
    green_mean = np.mean(combined[:, 1])
    
    return float(green_mean)


# =============================================================================
# UI DRAWING
# =============================================================================

def draw_face_box(
    frame: np.ndarray,
    face_landmarks,
    color: Tuple[int, int, int],
    label: str,
    confidence: Optional[float] = None
) -> None:
    """
    Draw bounding box around face with status label.
    
    Args:
        frame: Image to draw on (modified in place)
        face_landmarks: MediaPipe face landmarks
        color: BGR color for box
        label: Status text
        confidence: Optional confidence percentage
    """
    h, w = frame.shape[:2]
    
    # Get bounding box from landmarks
    xs = [int(lm.x * w) for lm in face_landmarks.landmark]
    ys = [int(lm.y * h) for lm in face_landmarks.landmark]
    
    x_min, x_max = max(0, min(xs) - 20), min(w, max(xs) + 20)
    y_min, y_max = max(0, min(ys) - 40), min(h, max(ys) + 20)
    
    # Draw box
    thickness = 3
    cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), color, thickness)
    
    # Draw corner accents
    corner_len = 30
    cv2.line(frame, (x_min, y_min), (x_min + corner_len, y_min), color, thickness + 2)
    cv2.line(frame, (x_min, y_min), (x_min, y_min + corner_len), color, thickness + 2)
    cv2.line(frame, (x_max, y_min), (x_max - corner_len, y_min), color, thickness + 2)
    cv2.line(frame, (x_max, y_min), (x_max, y_min + corner_len), color, thickness + 2)
    cv2.line(frame, (x_min, y_max), (x_min + corner_len, y_max), color, thickness + 2)
    cv2.line(frame, (x_min, y_max), (x_min, y_max - corner_len), color, thickness + 2)
    cv2.line(frame, (x_max, y_max), (x_max - corner_len, y_max), color, thickness + 2)
    cv2.line(frame, (x_max, y_max), (x_max, y_max - corner_len), color, thickness + 2)
    
    # Draw label background
    label_text = label
    if confidence is not None:
        label_text += f" ({confidence:.0f}%)"
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.7
    (text_w, text_h), _ = cv2.getTextSize(label_text, font, font_scale, 2)
    
    cv2.rectangle(
        frame,
        (x_min, y_min - text_h - 15),
        (x_min + text_w + 10, y_min - 5),
        color,
        -1
    )
    
    # Draw label text
    cv2.putText(
        frame,
        label_text,
        (x_min + 5, y_min - 12),
        font,
        font_scale,
        (0, 0, 0),
        2
    )


def draw_signal_graph(
    frame: np.ndarray,
    signal_buffer: deque,
    x: int,
    y: int,
    width: int,
    height: int
) -> None:
    """
    Draw real-time signal graph in corner of frame.
    
    Args:
        frame: Image to draw on
        signal_buffer: Deque of green channel values
        x, y: Top-left corner of graph
        width, height: Graph dimensions
    """
    if len(signal_buffer) < 2:
        return
    
    # Draw background
    overlay = frame.copy()
    cv2.rectangle(overlay, (x, y), (x + width, y + height), COLOR_GRAPH_BG, -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
    
    # Draw border
    cv2.rectangle(frame, (x, y), (x + width, y + height), (60, 60, 60), 1)
    
    # Draw grid lines
    for i in range(1, 4):
        grid_y = y + (height * i) // 4
        cv2.line(frame, (x, grid_y), (x + width, grid_y), (50, 50, 50), 1)
    
    # Normalize signal for display
    signal = np.array(signal_buffer)
    if np.std(signal) > 0:
        signal_norm = (signal - np.min(signal)) / (np.max(signal) - np.min(signal) + 1e-10)
    else:
        signal_norm = np.ones_like(signal) * 0.5
    
    # Draw signal line (vectorized point calculation)
    points = []
    for i, val in enumerate(signal_norm):
        px = x + int((i / (len(signal_norm) - 1)) * width)
        py = y + height - int(val * (height - 10)) - 5
        points.append([px, py])
    
    points = np.array(points, dtype=np.int32)
    cv2.polylines(frame, [points], False, COLOR_GRAPH_LINE, 2, cv2.LINE_AA)
    
    # Draw label
    cv2.putText(frame, "rPPG Signal", (x + 5, y + 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)


def draw_status_hud(
    frame: np.ndarray,
    fps: float,
    buffer_progress: float,
    bpm: Optional[float],
    is_live: bool
) -> None:
    """
    Draw HUD overlay with status information.
    
    Args:
        frame: Image to draw on
        fps: Current frames per second
        buffer_progress: 0-1 progress of filling signal buffer
        bpm: Detected BPM or None
        is_live: Whether liveness is detected
    """
    h, w = frame.shape[:2]
    
    # Top-left status
    y_offset = 30
    cv2.putText(frame, f"FPS: {fps:.1f}", (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1)
    
    # Buffer progress bar
    y_offset += 30
    bar_width = 150
    bar_height = 8
    progress_width = int(buffer_progress * bar_width)
    
    cv2.rectangle(frame, (10, y_offset), (10 + bar_width, y_offset + bar_height),
                  (60, 60, 60), -1)
    cv2.rectangle(frame, (10, y_offset), (10 + progress_width, y_offset + bar_height),
                  COLOR_SCANNING, -1)
    cv2.putText(frame, f"Buffer: {buffer_progress*100:.0f}%", (10, y_offset + 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
    
    # BPM display (large, centered at top)
    if bpm is not None:
        bpm_text = f"{int(bpm)} BPM"
        font_scale = 1.5
        (text_w, text_h), _ = cv2.getTextSize(bpm_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 3)
        
        text_x = (w - text_w) // 2
        text_y = 50
        
        # Draw heart icon (pulsing effect)
        heart_x = text_x - 50
        heart_color = COLOR_LIVENESS if is_live else COLOR_DEEPFAKE
        cv2.putText(frame, "♥", (heart_x, text_y + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, heart_color, 2)
        
        cv2.putText(frame, bpm_text, (text_x, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, COLOR_LIVENESS, 3)
    
    # Instructions at bottom
    instructions = "Press 'Q' to quit | Press 'R' to reset buffer"
    (text_w, _), _ = cv2.getTextSize(instructions, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    cv2.putText(frame, instructions, ((w - text_w) // 2, h - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)


# =============================================================================
# MAIN DETECTOR CLASS
# =============================================================================

class LivenessDetector:
    """
    Bio-liveness detector using rPPG (Remote Photoplethysmography).
    
    This class encapsulates the entire detection pipeline:
    1. Face detection using MediaPipe Face Mesh
    2. ROI extraction from forehead and cheeks
    3. Green channel signal accumulation
    4. FFT-based heart rate detection
    5. Liveness classification
    """
    
    def __init__(self):
        # Initialize MediaPipe Face Mesh
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,  # Includes iris landmarks
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Signal buffer for FFT analysis
        self.signal_buffer = deque(maxlen=BUFFER_SIZE)
        
        # FPS tracking
        self.fps_buffer = deque(maxlen=30)
        self.last_frame_time = time.time()
        self.current_fps = 30.0
        
        # Bandpass filter (initialized when we know actual fps)
        self.filter_b = None
        self.filter_a = None
        
        # Detection state
        self.last_bpm = None
        self.last_confidence = None
        self.is_live = False
        self.consecutive_detections = 0
    
    def reset(self):
        """Clear signal buffer and reset detection state"""
        self.signal_buffer.clear()
        self.last_bpm = None
        self.last_confidence = None
        self.is_live = False
        self.consecutive_detections = 0
    
    def update_fps(self):
        """Update FPS calculation"""
        current_time = time.time()
        frame_time = current_time - self.last_frame_time
        self.last_frame_time = current_time
        
        if frame_time > 0:
            self.fps_buffer.append(1.0 / frame_time)
            self.current_fps = np.mean(self.fps_buffer)
            
            # Update bandpass filter if fps changed significantly
            if self.filter_b is None or len(self.fps_buffer) == 30:
                self.filter_b, self.filter_a = create_bandpass_filter(
                    LOWCUT_HZ, HIGHCUT_HZ, self.current_fps
                )
    
    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Process a single frame and return annotated output.
        
        Pipeline:
        1. Detect face and extract landmarks
        2. Extract green channel mean from ROIs
        3. Add to signal buffer
        4. If buffer full, perform FFT analysis
        5. Draw UI overlay
        
        Args:
            frame: BGR image from webcam
        
        Returns:
            Annotated frame with detection results
        """
        self.update_fps()
        
        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect face mesh
        results = self.face_mesh.process(rgb_frame)
        
        output_frame = frame.copy()
        
        if results.multi_face_landmarks:
            face_landmarks = results.multi_face_landmarks[0]
            
            # Extract green channel mean from facial ROIs
            green_mean = get_green_channel_mean(frame, face_landmarks)
            
            if green_mean is not None:
                self.signal_buffer.append(green_mean)
            
            # Analyze signal if buffer is sufficiently full
            buffer_progress = len(self.signal_buffer) / BUFFER_SIZE
            
            if len(self.signal_buffer) >= BUFFER_SIZE // 2:
                self._analyze_signal()
            
            # Draw face box with detection result
            if self.is_live and self.last_bpm is not None:
                color = COLOR_LIVENESS
                label = f"LIVENESS DETECTED: {int(self.last_bpm)} BPM"
                confidence = self.last_confidence
            elif len(self.signal_buffer) < BUFFER_SIZE // 2:
                color = COLOR_SCANNING
                label = "SCANNING..."
                confidence = None
            else:
                color = COLOR_DEEPFAKE
                label = "⚠️ ARTIFICIAL / DEEPFAKE"
                confidence = 100 - (self.last_confidence or 0)
            
            draw_face_box(output_frame, face_landmarks, color, label, confidence)
            
            # Draw signal graph
            graph_width = 200
            graph_height = 80
            graph_x = frame.shape[1] - graph_width - 20
            graph_y = frame.shape[0] - graph_height - 60
            draw_signal_graph(output_frame, self.signal_buffer, 
                            graph_x, graph_y, graph_width, graph_height)
            
            # Draw HUD
            draw_status_hud(output_frame, self.current_fps, buffer_progress,
                          self.last_bpm if self.is_live else None, self.is_live)
        else:
            # No face detected
            cv2.putText(output_frame, "No face detected", 
                       (frame.shape[1]//2 - 100, frame.shape[0]//2),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 100, 100), 2)
        
        return output_frame
    
    def _analyze_signal(self):
        """
        Analyze accumulated signal using FFT.
        
        MATHEMATICAL PROCESS:
        =====================
        1. Apply bandpass filter to remove DC offset and high-frequency noise
        2. Compute FFT to get frequency spectrum
        3. Find peak in valid heart rate range (0.8-3.0 Hz)
        4. Calculate signal-to-noise ratio
        5. If SNR > threshold, compute BPM = peak_frequency × 60
        """
        signal = np.array(self.signal_buffer)
        
        # Apply bandpass filter if available
        if self.filter_b is not None and len(signal) > 15:
            try:
                signal_filtered = apply_bandpass_filter(signal, self.filter_b, self.filter_a)
            except Exception:
                signal_filtered = signal
        else:
            signal_filtered = signal
        
        # Compute FFT spectrum
        frequencies, magnitudes = compute_fft_spectrum(signal_filtered, self.current_fps)
        
        # Find heart rate peak
        peak_freq, peak_mag, noise_floor = find_heart_rate_peak(frequencies, magnitudes)
        
        # Calculate signal-to-noise ratio
        snr = peak_mag / noise_floor if noise_floor > 0 else 0
        
        if peak_freq is not None and snr >= PEAK_NOISE_THRESHOLD:
            # Valid heartbeat detected
            bpm = peak_freq * 60
            
            # Sanity check on BPM (physiological limits)
            if 45 <= bpm <= 200:
                self.last_bpm = bpm
                self.last_confidence = min(100, snr * 25)  # Scale SNR to percentage
                self.consecutive_detections += 1
                
                # Require 3 consecutive detections for stable "live" classification
                if self.consecutive_detections >= 3:
                    self.is_live = True
            else:
                self._decay_detection()
        else:
            self._decay_detection()
    
    def _decay_detection(self):
        """Gradually decay detection confidence"""
        self.consecutive_detections = max(0, self.consecutive_detections - 1)
        if self.consecutive_detections == 0:
            self.is_live = False
        self.last_confidence = max(0, (self.last_confidence or 0) - 10)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point for the liveness detector"""
    print("=" * 60)
    print("TrustSentinel Bio-Liveness Detector")
    print("=" * 60)
    print("\nInitializing webcam and face detection...")
    
    # Initialize webcam
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("ERROR: Could not open webcam")
        print("Make sure your webcam is connected and not in use by another application")
        sys.exit(1)
    
    # Set camera properties for optimal rPPG capture
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    # Get actual camera properties
    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"\nCamera initialized: {actual_width}x{actual_height} @ {actual_fps:.1f} fps")
    print("\nControls:")
    print("  Q - Quit")
    print("  R - Reset signal buffer")
    print("\nStarting detection loop...\n")
    
    # Initialize detector
    detector = LivenessDetector()
    
    # Main loop
    try:
        while True:
            ret, frame = cap.read()
            
            if not ret:
                print("WARNING: Failed to read frame from webcam")
                continue
            
            # Process frame
            output_frame = detector.process_frame(frame)
            
            # Display result
            cv2.imshow("TrustSentinel - Bio-Liveness Detector", output_frame)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q') or key == ord('Q'):
                print("\nExiting...")
                break
            elif key == ord('r') or key == ord('R'):
                print("Resetting signal buffer...")
                detector.reset()
    
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    
    finally:
        # Cleanup
        cap.release()
        cv2.destroyAllWindows()
        print("Cleanup complete. Goodbye!")


if __name__ == "__main__":
    main()
