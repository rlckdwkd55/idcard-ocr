from flask import Flask, request, jsonify, render_template, Response
import json
import cv2
import numpy as np
import easyocr

from roi_templates import DRIVER_TEMPLATES

app = Flask(__name__)

# EasyOCR 리더
reader = easyocr.Reader(['ko'], gpu=False)


def preprocess_for_ocr(crop):
    """
    OCR 정확도를 높이기 위한 전처리 함수

    1) 컬러 이미지를 흑백으로 변환
    2) Gaussian Blur로 노이즈 제거
    3) Otsu Thresholding으로 이진화
    """
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    gray = cv2.resize(gray, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, th = cv2.threshold(
        gray, 0, 255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    return th


@app.route("/")
def index():
    """테스트용 업로드 페이지"""
    return render_template("index.html")


@app.route("/api/ocr/id-card", methods=["POST"])
def ocr_id_card():
    """
    운전면허증 이미지 업로드 후,
    하드코딩된 ROI 영역별로 OCR 수행하여 JSON으로 반환하는 엔드포인트
    """
    # 1) 이미지 & 카드 타입 받기
    file = request.files.get("image")
    card_type = request.form.get("card_type", "driver_license_v1")

    if not file:
        return jsonify({"ok": False, "error": "image file is required"}), 400

    if card_type not in DRIVER_TEMPLATES:
        return jsonify(
            {"ok": False, "error": f"unknown card_type: {card_type}"}
        ), 400

    tmpl = DRIVER_TEMPLATES[card_type]
    base_w = tmpl["base_width"]
    base_h = tmpl["base_height"]

    # 2) 이미지 디코딩
    img_bytes = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)
    if img is None:
        return jsonify({"ok": False, "error": "cannot decode image"}), 400

    # 3) 기준 해상도로 resize (좌표와 맞추기)
    resized = cv2.resize(img, (base_w, base_h), interpolation=cv2.INTER_AREA)

    results = []

    SHOW_DEBUG_CROPS = True

    # 4) 각 필드별로 crop + 전처리 + OCR
    for field_name, roi in tmpl["fields"].items():
        x, y, w_roi, h_roi = roi["x"], roi["y"], roi["w"], roi["h"]

        crop = resized[y:y + h_roi, x:x + w_roi]
        if crop.size == 0:
            results.append({
                "field": field_name,
                "bbox": {"x": x, "y": y, "w": w_roi, "h": h_roi},
                "text": "",
                "confidence": 0.0,
                "error": "empty crop"
            })
            continue

        # 디버그 crop 팝업
        if SHOW_DEBUG_CROPS:
            debug_window_name = f"crop: {field_name} ({x},{y},{w_roi},{h_roi})"
        cv2.imshow(debug_window_name, crop)
        cv2.waitKey(0)  # 키를 눌러야 다음 필드로 진행
        cv2.destroyWindow(debug_window_name)

        # 전처리
        proc = preprocess_for_ocr(crop)

        # OCR 수행
        ocr_result = reader.readtext(proc, detail=1)

        text_lines = []
        confidences = []
        for box, text, conf in ocr_result:
            text_lines.append(text)
            confidences.append(float(conf))

        if text_lines:
            text_final = " ".join(text_lines)
            conf_final = float(sum(confidences) / len(confidences))
        else:
            text_final = ""
            conf_final = 0.0

        results.append({
            "field": field_name,
            "bbox": {"x": x, "y": y, "w": w_roi, "h": h_roi},
            "text": text_final,
            "confidence": conf_final,
        })

    response_body = {
        "ok": True,
        "card_type": card_type,
        "results": results,
    }

    return Response(
        json.dumps(response_body, ensure_ascii=False),
        content_type="application/json; charset=utf-8"
    )


if __name__ == "__main__":
    # 로컬 개발용 실행
    app.run(host="0.0.0.0", port=5000, debug=True)
