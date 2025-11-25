console.log("OCR JS loaded");

const form = document.getElementById('ocr-form');
const imageInput = document.getElementById('image-input');
const imagePreview = document.getElementById('image-preview');
const previewPlaceholder = document.getElementById('preview-placeholder');
const jsonOutput = document.getElementById('json-output');
const errorMessage = document.getElementById('error-message');

// 이미지 미리보기
imageInput.addEventListener('change', () => {
    const file = imageInput.files[0];
    if (!file) {
        imagePreview.style.display = 'none';
        previewPlaceholder.style.display = 'block';
        return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
        imagePreview.src = e.target.result;
        imagePreview.style.display = 'block';
        previewPlaceholder.style.display = 'none';
    };
    reader.readAsDataURL(file);
});

// 폼 submit → fetch로 API 호출
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorMessage.style.display = 'none';

    const file = imageInput.files[0];
    if (!file) {
        errorMessage.textContent = '이미지를 선택하세요.';
        errorMessage.style.display = 'block';
        return;
    }

    const formData = new FormData(form);

    jsonOutput.classList.remove('empty');
    jsonOutput.textContent = '요청 중입니다...';

    try {
        const res = await fetch('/api/ocr/id-card', {
            method: 'POST',
            body: formData
        });

        if (!res.ok) {
            const errorText = await res.text();
            jsonOutput.textContent = `오류 응답: ${res.status}\n${errorText}`;
            return;
        }

        const data = await res.json();

        jsonOutput.textContent = JSON.stringify(data, null, 2);

    } catch (err) {
        console.error(err);
        jsonOutput.textContent = '요청 중 오류가 발생했습니다.';
    }
});
