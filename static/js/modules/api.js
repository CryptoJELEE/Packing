/**
 * API 호출 관련 모듈
 */

/**
 * 마스터 상태 확인
 */
export async function getMasterStatus() {
    const response = await fetch('/api/getMasterStatus');

    if (!response.ok) {
        throw new Error(`서버 오류 (${response.status})`);
    }

    return await response.json();
}

/**
 * 마스터 데이터 업로드
 */
export async function uploadMaster(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch('/api/uploadMaster', {
        method: 'POST',
        body: formData
    });

    return handleResponse(response);
}

/**
 * 주문서 업로드
 */
export async function uploadOrder(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch('/api/uploadOrder', {
        method: 'POST',
        body: formData
    });

    return handleResponse(response);
}

/**
 * CSV 파일 업로드
 */
export async function uploadCSV(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch('/api/uploadCSV', {
        method: 'POST',
        body: formData
    });

    return handleResponse(response);
}

/**
 * CSV 아이템 조회
 */
export async function getCSVItems(sessionId, categories = []) {
    const params = new URLSearchParams();
    params.append('session_id', sessionId);
    categories.forEach(cat => params.append('categories', cat));

    const response = await fetch(`/api/getCSVItems?${params.toString()}`);
    return handleResponse(response);
}

/**
 * 시뮬레이션 실행
 */
export async function runVisualization(requestData) {
    const response = await fetch('/api/visualize', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
    });

    return handleResponse(response);
}

/**
 * 상세 보고서 조회
 */
export async function getDetailedReport(sessionId) {
    const response = await fetch(`/api/getDetailedReport/${sessionId}`);
    return handleResponse(response);
}

/**
 * 응답 처리 헬퍼
 */
async function handleResponse(response) {
    if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = `서버 오류 (${response.status})`;

        if (response.status === 404) {
            errorMessage = 'API 엔드포인트를 찾을 수 없습니다. 서버가 제대로 시작되었는지 확인하세요.';
        } else if (errorText) {
            try {
                const errorData = JSON.parse(errorText);
                errorMessage = errorData.Reason || errorData.message || errorMessage;
            } catch {
                errorMessage = errorText || errorMessage;
            }
        }
        throw new Error(errorMessage);
    }

    return await response.json();
}
