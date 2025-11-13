/**
 * 파일 업로드 관련 모듈
 */

import * as API from './api.js';
import * as UI from './ui.js';

/**
 * 파일 정보 표시
 */
function displayFileInfo(file, targetElement) {
    if (targetElement) {
        targetElement.style.display = 'block';
        targetElement.innerHTML = `
            <strong>선택된 파일:</strong> ${file.name}<br>
            <strong>크기:</strong> ${(file.size / 1024).toFixed(2)} KB
        `;
    }
}

/**
 * 마스터 파일 선택 핸들러
 */
export function handleMasterFileSelect(event, state) {
    const file = event.target.files[0];
    if (file) {
        const fileInfo = document.getElementById('master-file-info');
        const uploadBtn = document.getElementById('master-upload-btn');

        displayFileInfo(file, fileInfo);
        if (uploadBtn) {
            uploadBtn.disabled = false;
        }
    }
}

/**
 * 마스터 업로드 핸들러
 */
export async function handleMasterUpload(state) {
    const fileInput = document.getElementById('master-file');
    const file = fileInput?.files[0];
    const statusElement = document.getElementById('master-upload-status');
    const uploadBtn = document.getElementById('master-upload-btn');

    if (!file) {
        UI.showStatus('파일을 선택해주세요.', 'error', statusElement);
        return;
    }

    UI.showLoading(true);
    if (uploadBtn) uploadBtn.disabled = true;

    try {
        const data = await API.uploadMaster(file);

        if (data.Success) {
            UI.showStatus(data.message, 'success', statusElement);
            state.hasMasterData = true;
            await checkMasterStatus(state);
            UI.showSection('order-section', true);
        } else {
            UI.showStatus(`오류: ${data.Reason}`, 'error', statusElement);
        }
    } catch (error) {
        UI.showStatus(`업로드 오류: ${error.message}`, 'error', statusElement);
    } finally {
        UI.showLoading(false);
        if (uploadBtn) uploadBtn.disabled = false;
    }
}

/**
 * 주문서 파일 선택 핸들러
 */
export function handleOrderFileSelect(event, state) {
    const file = event.target.files[0];
    if (file) {
        const fileInfo = document.getElementById('order-file-info');
        const uploadBtn = document.getElementById('order-upload-btn');

        displayFileInfo(file, fileInfo);
        if (uploadBtn) {
            uploadBtn.disabled = false;
        }
    }
}

/**
 * 주문서 업로드 핸들러
 */
export async function handleOrderUpload(state) {
    const fileInput = document.getElementById('order-file');
    const file = fileInput?.files[0];
    const statusElement = document.getElementById('order-upload-status');
    const uploadBtn = document.getElementById('order-upload-btn');
    const unmatchedElement = document.getElementById('order-unmatched');

    if (!state.hasMasterData) {
        UI.showStatus('먼저 자재마스터를 업로드해주세요.', 'error', statusElement);
        return;
    }

    if (!file) {
        UI.showStatus('파일을 선택해주세요.', 'error', statusElement);
        return;
    }

    UI.showLoading(true);
    if (uploadBtn) uploadBtn.disabled = true;

    try {
        const data = await API.uploadOrder(file);

        if (data.Success) {
            state.currentSessionId = data.session_id;
            state.currentItems = data.matched_items;

            UI.showStatus(
                `주문서 처리 완료: 매칭 ${data.matched_count}개, 미매칭 ${data.unmatched_count}개`,
                'success',
                statusElement
            );

            // 미매칭 아이템 표시
            if (unmatchedElement) {
                if (data.unmatched_items && data.unmatched_items.length > 0) {
                    unmatchedElement.style.display = 'block';
                    unmatchedElement.innerHTML = `
                        <h3>매칭되지 않은 아이템:</h3>
                        <ul>
                            ${data.unmatched_items.map(item =>
                                `<li><strong>${item.partno}</strong> - ${item.name} (수량: ${item.quantity}) - ${item.reason}</li>`
                            ).join('')}
                        </ul>
                    `;
                } else {
                    unmatchedElement.style.display = 'none';
                }
            }

            // 주문서 아이템 표시
            UI.displayOrderItems(data.matched_items || []);

            // 섹션 표시
            UI.showSection('order-items-section', true);
            UI.showSection('box-section', true);
            UI.showSection('sim-section', true);
        } else {
            UI.showStatus(`오류: ${data.Reason}`, 'error', statusElement);
        }
    } catch (error) {
        UI.showStatus(`업로드 오류: ${error.message}`, 'error', statusElement);
    } finally {
        UI.showLoading(false);
        if (uploadBtn) uploadBtn.disabled = false;
    }
}

/**
 * CSV 파일 선택 핸들러
 */
export function handleCSVFileSelect(event, state) {
    const file = event.target.files[0];
    if (file) {
        const fileInfo = document.getElementById('file-info');
        const uploadBtn = document.getElementById('upload-btn');

        displayFileInfo(file, fileInfo);
        if (uploadBtn) {
            uploadBtn.disabled = false;
        }
    }
}

/**
 * CSV 업로드 핸들러
 */
export async function handleCSVUpload(state) {
    const fileInput = document.getElementById('csv-file');
    const file = fileInput?.files[0];
    const statusElement = document.getElementById('upload-status');
    const uploadBtn = document.getElementById('upload-btn');

    if (!file) {
        UI.showStatus('파일을 선택해주세요.', 'error', statusElement);
        return;
    }

    UI.showLoading(true);
    if (uploadBtn) uploadBtn.disabled = true;

    try {
        const data = await API.uploadCSV(file);

        if (data.Success) {
            state.currentSessionId = data.session_id;
            state.currentStats = data.stats || {};
            state.currentItems = data.items || [];

            UI.showStatus('CSV 파일이 성공적으로 처리되었습니다.', 'success', statusElement);

            if (data.stats) {
                UI.displayStats(data.stats);
            }

            UI.displayItems(data.items || []);

            // 섹션 표시
            UI.showSection('stats-section', true);
            UI.showSection('box-section', true);
            UI.showSection('items-section', true);
            UI.showSection('sim-section', true);

            // 카테고리 필터 생성
            if (data.stats?.by_category) {
                createCategoryFilters(data.stats.by_category, state);
            }
        } else {
            UI.showStatus(`오류: ${data.Reason}`, 'error', statusElement);
        }
    } catch (error) {
        UI.showStatus(`업로드 오류: ${error.message}`, 'error', statusElement);
    } finally {
        UI.showLoading(false);
        if (uploadBtn) uploadBtn.disabled = false;
    }
}

/**
 * 마스터 상태 확인
 */
export async function checkMasterStatus(state) {
    const masterStatus = document.getElementById('master-status');
    if (!masterStatus) return;

    try {
        const data = await API.getMasterStatus();

        if (data.Success && data.has_master) {
            state.hasMasterData = true;
            masterStatus.innerHTML = `
                <div class="status-message success">
                    <strong>마스터 데이터 로드됨:</strong> ${data.stats.total_items}개 항목
                </div>
            `;
            UI.showSection('order-section', true);
        } else {
            state.hasMasterData = false;
            masterStatus.innerHTML = `
                <div class="status-message warning">
                    마스터 데이터가 없습니다. 먼저 자재마스터를 업로드해주세요.
                </div>
            `;
            UI.showSection('order-section', false);
        }
    } catch (error) {
        // 마스터 상태 확인 실패는 조용히 처리
        if (process.env.NODE_ENV === 'development') {
            console.error('마스터 상태 확인 오류:', error);
        }
    }
}

/**
 * 카테고리 필터 생성
 */
function createCategoryFilters(categories, state) {
    const categoryFilters = document.getElementById('category-filters');
    if (!categoryFilters) return;

    categoryFilters.innerHTML = Object.keys(categories).map(cat =>
        `<span class="category-filter" data-category="${cat}">${cat}</span>`
    ).join('');

    // 필터 클릭 이벤트
    document.querySelectorAll('.category-filter').forEach(filter => {
        filter.addEventListener('click', function() {
            this.classList.toggle('active');
            const category = this.dataset.category;

            if (this.classList.contains('active')) {
                if (!state.selectedCategories.includes(category)) {
                    state.selectedCategories.push(category);
                }
            } else {
                state.selectedCategories = state.selectedCategories.filter(c => c !== category);
            }

            filterItems(state);
        });
    });
}

/**
 * 아이템 필터링
 */
async function filterItems(state) {
    if (!state.currentSessionId) return;

    UI.showLoading(true);

    try {
        const data = await API.getCSVItems(state.currentSessionId, state.selectedCategories);

        if (data.Success) {
            UI.displayItems(data.items);
        } else {
            UI.showStatus(`필터링 오류: ${data.Reason}`, 'error');
        }
    } catch (error) {
        UI.showStatus(`필터링 오류: ${error.message}`, 'error');
    } finally {
        UI.showLoading(false);
    }
}
