"""
AgroTrack AI Image Quality Validation Engine
Analyzes leaf photo quality before machine learning inference:
- Resolution & dimensions
- Blurriness / focus via Laplacian variance
- Exposure (underexposure / overexposure)
- Contrast and color distribution
"""

import io
from typing import Dict, Any, List
import cv2
import numpy as np
from PIL import Image

MIN_WIDTH = 100
MIN_HEIGHT = 100
MIN_BRIGHTNESS = 20.0     # Mean pixel brightness (0-255)
MAX_BRIGHTNESS = 245.0
BLUR_THRESHOLD = 15.0     # Laplacian variance threshold below which image is blurry


def is_valid_image_header(data: bytes) -> bool:
    """
    Verifies magic bytes of uploaded image data to prevent spoofed MIME types and polyglots.
    Supports genuine JPEG, PNG, and WebP signatures.
    """
    if not data or len(data) < 12:
        return False
    # JPEG signature: FF D8 FF
    if data.startswith(b"\xff\xd8\xff"):
        return True
    # PNG signature: 89 50 4E 47 0D 0A 1A 0A
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return True
    # WebP signature: RIFF .... WEBP
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return True
    return False


def validate_image_quality(image_bytes: bytes) -> Dict[str, Any]:
    """
    Performs comprehensive computer vision quality checks on an image.
    Returns:
        dict containing validation outcome, metrics, warnings, and quality rating.
    """
    warnings: List[str] = []

    # 0. Magic Bytes Validation
    if not is_valid_image_header(image_bytes):
        return {
            "is_valid": False,
            "width": 0,
            "height": 0,
            "brightness": 0.0,
            "sharpness": 0.0,
            "quality_status": "Invalid",
            "warnings": ["File content fails magic byte verification (unrecognized image binary signature)."],
            "message": "Invalid or forged image binary header. Please upload genuine JPEG, PNG, or WebP files."
        }
    
    # 1. Attempt basic image decoding
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_bgr is None:
            return {
                "is_valid": False,
                "width": 0,
                "height": 0,
                "brightness": 0.0,
                "sharpness": 0.0,
                "quality_status": "Invalid",
                "warnings": ["File content could not be decoded as an image."],
                "message": "Invalid image file format or corrupted bytes."
            }
    except Exception as e:
        return {
            "is_valid": False,
            "width": 0,
            "height": 0,
            "brightness": 0.0,
            "sharpness": 0.0,
            "quality_status": "Invalid",
            "warnings": [f"Image decode error: {str(e)}"],
            "message": "Could not read image file."
        }

    h, w, _ = img_bgr.shape

    # 2. Resolution Check
    if w < MIN_WIDTH or h < MIN_HEIGHT:
        warnings.append(f"Image resolution too low ({w}x{h}px). Minimum required is {MIN_WIDTH}x{MIN_HEIGHT}px.")

    # 3. Grayscale conversion for brightness and sharpness analysis
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # 4. Brightness / Exposure Check
    brightness = float(np.mean(gray))
    if brightness < MIN_BRIGHTNESS:
        warnings.append(f"Image is severely underexposed (brightness: {brightness:.1f}/255). Please ensure good ambient lighting.")
    elif brightness > MAX_BRIGHTNESS:
        warnings.append(f"Image is overexposed (brightness: {brightness:.1f}/255). Avoid direct camera flash glare.")

    # 5. Sharpness / Blur Detection (Laplacian Variance)
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    if laplacian_var < BLUR_THRESHOLD:
        warnings.append(f"Image is out of focus or blurry (sharpness score: {laplacian_var:.1f}). Hold camera steady close to leaf.")

    # 6. Overall Quality Determination
    is_valid = (w >= MIN_WIDTH and h >= MIN_HEIGHT and brightness >= 10.0 and brightness <= 250.0)

    if not is_valid:
        quality_status = "Poor (Unacceptable)"
        message = "Image quality is insufficient for accurate agricultural diagnosis."
    elif len(warnings) > 0:
        quality_status = "Suboptimal"
        message = "Image accepted, but some quality factors may slightly lower diagnostic confidence."
    else:
        quality_status = "Optimal"
        message = "Image quality is excellent for crop disease scanning."

    return {
        "is_valid": is_valid,
        "width": w,
        "height": h,
        "brightness": round(brightness, 1),
        "sharpness": round(laplacian_var, 1),
        "quality_status": quality_status,
        "warnings": warnings,
        "message": message
    }
