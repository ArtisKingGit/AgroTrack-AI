"""
Automated tests for preserving existing AgroFast AI / ML capabilities.
Tests:
- Input validation (file size, mime types)
- Image classification and PlantCV spot detection
- Treatment knowledgebase
"""

import io
from PIL import Image


def test_predict_validation_rejects_non_image(client):
    """Verifies that non-image file uploads return 400 Bad Request."""
    fake_txt = io.BytesIO(b"this is not an image file")
    files = {"image": ("test.txt", fake_txt, "text/plain")}
    response = client.post("/predict", files=files)
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["error"]


def test_predict_runs_model_inference_on_valid_image(client):
    """
    Verifies that a valid RGB image is processed by MobileNetV2 and returns
    crop, disease, confidence, treatment, and spot bounding boxes.
    """
    # Create a synthetic 224x224 RGB image
    img = Image.new("RGB", (224, 224), color=(34, 139, 34))  # Forest green leaf color
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    files = {"image": ("synthetic_leaf.jpg", buf, "image/jpeg")}
    response = client.post("/predict", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "crop" in data
    assert "disease" in data
    assert "confidence" in data
    assert "treatment" in data
    assert "boxes" in data
    assert isinstance(data["boxes"], list)


def test_treatments_knowledgebase_integrity():
    """Verifies that treatments mapping module is functional and covers key crops."""
    from backend.ai.treatments import get_treatment, PLANTVILLAGE_TREATMENTS

    assert len(PLANTVILLAGE_TREATMENTS) > 10

    # Test Apple Scab diagnosis
    res = get_treatment("Apple___Apple_scab")
    assert res["crop"] == "Apple"
    assert "Apple Scab" in res["disease"]
    assert "fungicide" in res["treatment"].lower() or "prune" in res["treatment"].lower()

    # Test healthy crop
    res_healthy = get_treatment("Tomato_healthy")
    assert "Healthy" in res_healthy["disease"]
