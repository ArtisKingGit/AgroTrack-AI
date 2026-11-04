# pyrefly: ignore [missing-import]
import cv2
# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
from plantcv import plantcv as pcv


def detect_disease(image_bytes, diagnosis_data):
    """
    Uses PlantCV for spot segmentation to produce bounding boxes.

    Classification (crop/disease/confidence) is no longer re-computed here —
    it is reused from classifier.predict_crop(), which already ran the model
    on this same image. Running the same 224x224 image through the model
    twice per request (once here, once in classifier.py) doubled inference
    latency and memory (two loaded copies of crop_model.keras) for no benefit.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    boxes = []
    is_healthy = diagnosis_data.get("disease", "Healthy").lower().startswith("healthy")
    if img_cv is not None and not diagnosis_data.get("is_soil") and not is_healthy:
        try:
            pcv.params.debug = None

            # Convert to grayscale (Value in HSV)
            v_channel = pcv.rgb2gray_hsv(rgb_img=img_cv, channel='v')

            # Thresholding to find dark or discolored spots
            bin_mask = pcv.threshold.binary(gray_img=v_channel, threshold=100, object_type='dark')

            # Fill small holes/spots to denoise
            bin_mask = pcv.fill(bin_mask, 200)

            # Compute disease spot pixel coverage / severity
            diseased_pixels = cv2.countNonZero(bin_mask)
            total_pixels = img_cv.shape[0] * img_cv.shape[1]
            severity_percentage = round((diseased_pixels / total_pixels) * 100, 2)

            # Find contours directly on binary mask using OpenCV
            contours, _ = cv2.findContours(bin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Create bounding boxes for detected regions
            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                # Filter for significant spots only (at least 500 pixels area)
                if w * h > 500:
                    boxes.append({"x": int(x), "y": int(y), "width": int(w), "height": int(h)})
        except Exception as e:
            print(f"Error in PlantCV spot detection: {e}")

    # Determine severity label
    if is_healthy or diagnosis_data.get("is_soil"):
        severity_percentage = 0.0
        severity_level = "None (Healthy)"
    elif len(boxes) > 0:
        if severity_percentage < 3.0:
            severity_level = "Mild (Early Stage)"
        elif severity_percentage < 15.0:
            severity_level = "Moderate"
        else:
            severity_level = "Severe (Advanced Infection)"
    else:
        # Fallback for diffuse discoloration without discrete spot contours
        severity_percentage = 10.0
        severity_level = "Diffuse Infection"

    # Fallback: if no specific spots found, use full image box (only for diseased/unhealthy scans)
    if not boxes and img_cv is not None and not is_healthy:
        h, w, _ = img_cv.shape
        boxes = [{"x": 0, "y": 0, "width": w, "height": h}]

    return {
        "boxes": boxes,
        "severity_percentage": severity_percentage,
        "severity_level": severity_level
    }
