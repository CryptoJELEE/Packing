// 전역 변수
let currentSessionId = null;
let currentItems = [];
let currentStats = null;
let selectedCategories = [];
let hasMasterData = false;

// DOM 요소
const masterFileInput = document.getElementById('master-file');
const masterUploadBtn = document.getElementById('master-upload-btn');
const masterFileInfo = document.getElementById('master-file-info');
const masterUploadStatus = document.getElementById('master-upload-status');
const masterStatus = document.getElementById('master-status');
const orderSection = document.getElementById('order-section');
const orderFileInput = document.getElementById('order-file');
const orderUploadBtn = document.getElementById('order-upload-btn');
const orderFileInfo = document.getElementById('order-file-info');
const orderUploadStatus = document.getElementById('order-upload-status');
const orderItemsSection = document.getElementById('order-items-section');
const orderItemsList = document.getElementById('order-items-list');
const orderUnmatched = document.getElementById('order-unmatched');

const csvFileInput = document.getElementById('csv-file');
const uploadBtn = document.getElementById('upload-btn');
const fileInfo = document.getElementById('file-info');
const uploadStatus = document.getElementById('upload-status');
const statsSection = document.getElementById('stats-section');
const boxSection = document.getElementById('box-section');
const itemsSection = document.getElementById('items-section');
const simSection = document.getElementById('sim-section');
const resultsSection = document.getElementById('results-section');
const loadingOverlay = document.getElementById('loading-overlay');

// 이벤트 리스너
if (masterFileInput) {
    masterFileInput.addEventListener('change', handleMasterFileSelect);
    masterUploadBtn.addEventListener('click', handleMasterUpload);
}
if (orderFileInput) {
    orderFileInput.addEventListener('change', handleOrderFileSelect);
    orderUploadBtn.addEventListener('click', handleOrderUpload);
}
if (csvFileInput) {
    csvFileInput.addEventListener('change', handleFileSelect);
    uploadBtn.addEventListener('click', handleUpload);
}
document.getElementById('run-simulation-btn').addEventListener('click', runSimulation);
document.getElementById('download-report-btn').addEventListener('click', downloadReport);
document.getElementById('view-detailed-report-btn').addEventListener('click', viewDetailedReport);
document.getElementById('view-work-instruction-btn').addEventListener('click', viewWorkInstruction);

// 파레트 모드 변경 시 지지면 비율 입력 비활성화
const isPalletCheckbox = document.getElementById('is-pallet');
if (isPalletCheckbox) {
    isPalletCheckbox.addEventListener('change', function() {
        const supportRatioInput = document.getElementById('support-ratio');
        const checkStableCheckbox = document.getElementById('check-stable');
        
        if (this.checked) {
            // 파레트 모드: 지지면 비율 체크 비활성화
            supportRatioInput.disabled = true;
            supportRatioInput.value = '0';
            // 안정성 검사는 유지하되, 바닥에 직접 올라가는 경우는 체크하지 않음
        } else {
            // 일반 모드: 지지면 비율 체크 활성화
            supportRatioInput.disabled = false;
            supportRatioInput.value = '0.75';
        }
    });
}

// 페이지 로드 시 마스터 상태 확인
checkMasterStatus();

// 파일 선택 처리
function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        fileInfo.style.display = 'block';
        fileInfo.innerHTML = `
            <strong>선택된 파일:</strong> ${file.name}<br>
            <strong>크기:</strong> ${(file.size / 1024).toFixed(2)} KB
        `;
        uploadBtn.disabled = false;
    }
}

// 파일 업로드 처리
async function handleUpload() {
    const file = csvFileInput.files[0];
    if (!file) {
        showStatus('파일을 선택해주세요.', 'error');
        return;
    }

    showLoading(true);
    uploadBtn.disabled = true;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/uploadCSV', {
            method: 'POST',
            body: formData
        });

        // 응답 상태 확인
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

        const data = await response.json();

        if (data.Success) {
            currentSessionId = data.session_id;
            currentStats = data.stats || {};
            currentItems = data.items || [];

            showStatus('CSV 파일이 성공적으로 처리되었습니다.', 'success');
            
            if (data.stats) {
                displayStats(data.stats);
            }
            
            if (data.items && Array.isArray(data.items)) {
                displayItems(data.items);
            } else {
                displayItems([]);
            }
            
            // 섹션 표시
            statsSection.style.display = 'block';
            boxSection.style.display = 'block';
            itemsSection.style.display = 'block';
            simSection.style.display = 'block';
        } else {
            showStatus(`오류: ${data.Reason}`, 'error');
        }
    } catch (error) {
        showStatus(`업로드 오류: ${error.message}`, 'error');
    } finally {
        showLoading(false);
        uploadBtn.disabled = false;
    }
}

// 통계 표시
function displayStats(stats) {
    // 안전 체크
    if (!stats) {
        const statsContent = document.getElementById('stats-content');
        statsContent.innerHTML = '<p>통계 데이터가 없습니다.</p>';
        return;
    }
    
    const statsContent = document.getElementById('stats-content');
    
    // 안전한 값 접근
    const totalItems = stats.total_items || 0;
    const totalVolume = (stats.total_volume !== undefined && stats.total_volume !== null) ? stats.total_volume : 0;
    const totalWeight = (stats.total_weight !== undefined && stats.total_weight !== null) ? stats.total_weight : 0;
    
    let html = `
        <div class="stat-box">
            <h3>전체 통계</h3>
            <p><strong>총 아이템 수:</strong> ${totalItems}개</p>
            <p><strong>총 부피:</strong> ${totalVolume.toFixed(2)} cm³</p>
            <p><strong>총 무게:</strong> ${totalWeight.toFixed(2)} kg</p>
        </div>
    `;

    if (stats.by_category && Object.keys(stats.by_category).length > 0) {
        html += `
            <div class="stat-box">
                <h3>카테고리별 분포</h3>
                <ul>
                    ${Object.entries(stats.by_category).map(([cat, count]) => 
                        `<li>${cat}: ${count}개</li>`
                    ).join('')}
                </ul>
            </div>
        `;
    }

    if (stats.by_packaging && Object.keys(stats.by_packaging).length > 0) {
        html += `
            <div class="stat-box">
                <h3>포장별 분포</h3>
                <ul>
                    ${Object.entries(stats.by_packaging).map(([pkg, count]) => 
                        `<li>${pkg}: ${count}개</li>`
                    ).join('')}
                </ul>
            </div>
        `;
    }

    statsContent.innerHTML = html;

    // 카테고리 필터 생성
    if (stats.by_category) {
        const categoryFilters = document.getElementById('category-filters');
        categoryFilters.innerHTML = Object.keys(stats.by_category).map(cat => 
            `<span class="category-filter" data-category="${cat}">${cat}</span>`
        ).join('');

        // 필터 클릭 이벤트
        document.querySelectorAll('.category-filter').forEach(filter => {
            filter.addEventListener('click', function() {
                this.classList.toggle('active');
                const category = this.dataset.category;
                if (this.classList.contains('active')) {
                    if (!selectedCategories.includes(category)) {
                        selectedCategories.push(category);
                    }
                } else {
                    selectedCategories = selectedCategories.filter(c => c !== category);
                }
                filterItems();
            });
        });
    }
}

// 아이템 표시
function displayItems(items) {
    // 안전 체크
    if (!items || !Array.isArray(items)) {
        const itemsList = document.getElementById('items-list');
        itemsList.innerHTML = '<p>아이템 데이터가 없습니다.</p>';
        return;
    }
    
    currentItems = items;
    const itemsList = document.getElementById('items-list');
    
    if (items.length === 0) {
        itemsList.innerHTML = '<p>표시할 아이템이 없습니다.</p>';
        return;
    }

    itemsList.innerHTML = items.map((item, index) => {
        // 안전한 데이터 접근
        const whd = item.WHD || [0, 0, 0];
        const original = item.original || {};
        const partno = item.partno || 'N/A';
        const name = item.name || '이름 없음';
        const weight = item.weight || 0;
        const typeofItem = item.typeof || 'cube';
        const category = original.분류 || '기타';
        
        return `
        <div class="item-card" data-index="${index}">
            <div class="item-info">
                <h4>${name}</h4>
                <p><strong>제품번호:</strong> ${partno}</p>
                <p><strong>크기:</strong> ${whd[0].toFixed(1)} × ${whd[1].toFixed(1)} × ${whd[2].toFixed(1)} cm</p>
                <p><strong>무게:</strong> ${weight} kg | <strong>타입:</strong> ${typeofItem} | <strong>분류:</strong> ${category}</p>
            </div>
            <div class="item-controls">
                <label>개수:</label>
                <input type="number" 
                       class="item-count" 
                       data-name="${name}" 
                       value="1" 
                       min="0" 
                       step="1">
            </div>
        </div>
        `;
    }).join('');
}

// 아이템 필터링
async function filterItems() {
    if (!currentSessionId) return;

    showLoading(true);

    try {
        const params = new URLSearchParams();
        params.append('session_id', currentSessionId);
        selectedCategories.forEach(cat => params.append('categories', cat));

        const response = await fetch(`/api/getCSVItems?${params.toString()}`);
        const data = await response.json();

        if (data.Success) {
            displayItems(data.items);
        } else {
            showStatus(`필터링 오류: ${data.Reason}`, 'error');
        }
    } catch (error) {
        showStatus(`필터링 오류: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// 시뮬레이션 실행
async function runSimulation() {
    if (!currentSessionId) {
        showStatus('먼저 CSV 파일을 업로드해주세요.', 'error');
        return;
    }

    showLoading(true);

    // 박스 설정 수집
    const boxData = {
        name: document.getElementById('box-name').value,
        WHD: [
            parseFloat(document.getElementById('box-width').value),
            parseFloat(document.getElementById('box-height').value),
            parseFloat(document.getElementById('box-depth').value)
        ],
        weight: parseFloat(document.getElementById('box-weight').value),
        coner: parseFloat(document.getElementById('box-corner').value),
        openTop: [1],
        is_pallet: document.getElementById('is-pallet').checked
    };

    // 아이템 개수 수집
    const itemCounts = {};
    
    // 주문서인 경우 자동으로 수량 설정
    if (currentItems && currentItems.length > 0 && currentItems[0] && currentItems[0].order_quantity) {
        // 주문서 아이템인 경우
        currentItems.forEach(item => {
            itemCounts[item.name] = item.order_quantity || 1;
        });
    } else {
        // 기존 방식 (직접 선택)
        document.querySelectorAll('.item-count').forEach(input => {
            const count = parseInt(input.value) || 0;
            if (count > 0) {
                itemCounts[input.dataset.name] = count;
            }
        });
    }

    // 시뮬레이션 파라미터
    const simParams = {
        bigger_first: document.getElementById('bigger-first').checked,
        fix_point: document.getElementById('fix-point').checked,
        check_stable: document.getElementById('check-stable').checked,
        support_surface_ratio: parseFloat(document.getElementById('support-ratio').value),
        distribute_items: true,
        use_advanced_strategy: document.getElementById('use-advanced-strategy').checked,
        try_multiple_strategies: document.getElementById('try-multiple-strategies').checked
    };

    const requestData = {
        session_id: currentSessionId,
        box: boxData,
        item_counts: itemCounts,
        simulation_params: simParams
    };

    try {
        const response = await fetch('/api/visualize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });

        // 응답 상태 확인
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

        const data = await response.json();

        if (data.Success) {
            displayResults(data);
            resultsSection.style.display = 'block';
            resultsSection.scrollIntoView({ behavior: 'smooth' });
            
            // 상세 보고서가 있으면 표시
            if (data.detailed_report && data.detailed_report.reports) {
                displayDetailedReports(data.detailed_report);
            }
        } else {
            showStatus(`시뮬레이션 오류: ${data.Reason}`, 'error');
        }
    } catch (error) {
        showStatus(`시뮬레이션 오류: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// 결과 표시
function displayResults(data) {
    const resultsStats = document.getElementById('results-stats');
    const resultsImages = document.getElementById('results-images');

    // 통계 표시
    if (data.result && data.result.bins) {
        let statsHtml = '';
        data.result.bins.forEach((bin, index) => {
            statsHtml += `
                <div class="stat-card">
                    <h3>${bin.space_utilization}%</h3>
                    <p>공간 활용률</p>
                </div>
                <div class="stat-card">
                    <h3>${bin.fitted_items}</h3>
                    <p>적재된 아이템</p>
                </div>
                <div class="stat-card">
                    <h3>${bin.unfitted_items}</h3>
                    <p>미적재 아이템</p>
                </div>
                <div class="stat-card">
                    <h3>${bin.weight_utilization.toFixed(1)}%</h3>
                    <p>무게 활용률</p>
                </div>
            `;
        });
        resultsStats.innerHTML = statsHtml;
    }

    // 이미지 표시
    if (data.images && data.images.length > 0) {
        resultsImages.innerHTML = data.images.map(image => `
            <div class="result-image">
                <img src="/api/image/${image}" alt="Packing Result">
            </div>
        `).join('');
    }
}

// 리포트 다운로드
function downloadReport() {
    if (!currentSessionId) {
        showStatus('리포트를 다운로드할 수 없습니다.', 'error');
        return;
    }

    window.location.href = `/api/report/${currentSessionId}`;
}

// 상세 보고서 보기
async function viewDetailedReport() {
    if (!currentSessionId) {
        showStatus('상세 보고서를 볼 수 없습니다.', 'error');
        return;
    }

    showLoading(true);

    try {
        const response = await fetch(`/api/getDetailedReport/${currentSessionId}`);
        const data = await response.json();

        if (data.Success && data.reports && Array.isArray(data.reports) && data.reports.length > 0) {
            const reportsList = document.getElementById('detailed-reports-list');
            reportsList.style.display = 'block';
            
            reportsList.innerHTML = `
                <h3>상세 보고서</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; margin-top: 15px;">
                    ${data.reports.map(report => {
                        const workInstructionUrl = `/api/workInstruction/${currentSessionId}/${report.bin_name}`;
                        return `
                        <div style="padding: 15px; background: #f8f9fa; border-radius: 6px; border: 1px solid #ddd;">
                            <h4>${report.bin_name}</h4>
                            <div style="display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap;">
                                <a href="${report.url}" target="_blank" class="btn btn-primary" style="display: inline-block; text-decoration: none; padding: 8px 15px; border-radius: 4px;">
                                    📊 상세 보고서
                                </a>
                                <a href="${workInstructionUrl}" target="_blank" class="btn btn-secondary" style="display: inline-block; text-decoration: none; padding: 8px 15px; border-radius: 4px; background: #28a745; color: white;">
                                    🖨️ 작업 지시서
                                </a>
                            </div>
                        </div>
                    `;
                    }).join('')}
                </div>
            `;
            
            reportsList.scrollIntoView({ behavior: 'smooth' });
        } else {
            showStatus('상세 보고서를 찾을 수 없습니다.', 'error');
        }
    } catch (error) {
        showStatus(`상세 보고서 조회 오류: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// 작업 지시서 보기
async function viewWorkInstruction() {
    if (!currentSessionId) {
        showStatus('작업 지시서를 볼 수 없습니다.', 'error');
        return;
    }

    showLoading(true);

    try {
        const response = await fetch(`/api/getDetailedReport/${currentSessionId}`);
        const data = await response.json();

        if (data.Success && data.reports && Array.isArray(data.reports) && data.reports.length > 0) {
            // 첫 번째 보고서의 작업 지시서 열기
            const firstReport = data.reports[0];
            if (firstReport && firstReport.bin_name) {
                const workInstructionUrl = `/api/workInstruction/${currentSessionId}/${firstReport.bin_name}`;
                try {
                    const newWindow = window.open(workInstructionUrl, '_blank');
                    if (!newWindow) {
                        // 팝업이 차단된 경우 현재 창에서 열기
                        window.location.href = workInstructionUrl;
                    }
                } catch (error) {
                    console.error('창 열기 오류:', error);
                    // 대안: 현재 창에서 열기
                    window.location.href = workInstructionUrl;
                }
                
                // 여러 보고서가 있으면 모두 열기 (지연 시간 증가로 팝업 차단 방지)
                if (data.reports.length > 1) {
                    setTimeout(() => {
                        data.reports.slice(1).forEach((report, index) => {
                            if (report && report.bin_name) {
                                const url = `/api/workInstruction/${currentSessionId}/${report.bin_name}`;
                                try {
                                    // 각 탭 사이에 추가 지연 (팝업 차단 방지)
                                    setTimeout(() => {
                                        const newWindow = window.open(url, '_blank');
                                        if (!newWindow) {
                                            console.warn(`팝업 차단: ${report.bin_name}`);
                                        }
                                    }, index * 300); // 각 탭마다 300ms 지연
                                } catch (error) {
                                    console.error(`창 열기 오류 (${report.bin_name}):`, error);
                                }
                            }
                        });
                    }, 1000); // 첫 번째 탭 후 1초 대기
                }
            }
        } else {
            showStatus('작업 지시서를 찾을 수 없습니다.', 'error');
        }
    } catch (error) {
        showStatus(`작업 지시서 조회 오류: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// 상태 메시지 표시
function showStatus(message, type) {
    uploadStatus.textContent = message;
    uploadStatus.className = `status-message ${type}`;
    uploadStatus.style.display = 'block';

    if (type === 'success') {
        setTimeout(() => {
            uploadStatus.style.display = 'none';
        }, 5000);
    }
}

// 로딩 오버레이 표시/숨김
function showLoading(show) {
    loadingOverlay.style.display = show ? 'flex' : 'none';
}

// 마스터 상태 확인
async function checkMasterStatus() {
    try {
        const response = await fetch('/api/getMasterStatus');
        
        // 응답 상태 확인
        if (!response.ok) {
            const errorText = await response.text();
            console.error(`서버 오류 (${response.status}): ${errorText}`);
            if (response.status === 404) {
                console.error('API 엔드포인트를 찾을 수 없습니다. 서버가 제대로 시작되었는지 확인하세요.');
            }
            return;
        }
        
        const data = await response.json();
        
        if (data.Success && data.has_master) {
            hasMasterData = true;
            masterStatus.innerHTML = `
                <div class="status-message success">
                    <strong>마스터 데이터 로드됨:</strong> ${data.stats.total_items}개 항목
                </div>
            `;
            orderSection.style.display = 'block';
        } else {
            hasMasterData = false;
            masterStatus.innerHTML = `
                <div class="status-message" style="background: #fff3cd; color: #856404; border: 1px solid #ffeaa7;">
                    마스터 데이터가 없습니다. 먼저 자재마스터를 업로드해주세요.
                </div>
            `;
            orderSection.style.display = 'none';
        }
    } catch (error) {
        console.error('마스터 상태 확인 오류:', error);
    }
}

// 마스터 파일 선택 처리
function handleMasterFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        masterFileInfo.style.display = 'block';
        masterFileInfo.innerHTML = `
            <strong>선택된 파일:</strong> ${file.name}<br>
            <strong>크기:</strong> ${(file.size / 1024).toFixed(2)} KB
        `;
        masterUploadBtn.disabled = false;
    }
}

// 마스터 업로드 처리
async function handleMasterUpload() {
    const file = masterFileInput.files[0];
    if (!file) {
        showStatus('파일을 선택해주세요.', 'error', masterUploadStatus);
        return;
    }

    showLoading(true);
    masterUploadBtn.disabled = true;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/uploadMaster', {
            method: 'POST',
            body: formData
        });

        // 응답 상태 확인
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

        const data = await response.json();

        if (data.Success) {
            showStatus(data.message, 'success', masterUploadStatus);
            hasMasterData = true;
            await checkMasterStatus();
            orderSection.style.display = 'block';
        } else {
            showStatus(`오류: ${data.Reason}`, 'error', masterUploadStatus);
        }
    } catch (error) {
        showStatus(`업로드 오류: ${error.message}`, 'error', masterUploadStatus);
    } finally {
        showLoading(false);
        masterUploadBtn.disabled = false;
    }
}

// 주문서 파일 선택 처리
function handleOrderFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        orderFileInfo.style.display = 'block';
        orderFileInfo.innerHTML = `
            <strong>선택된 파일:</strong> ${file.name}<br>
            <strong>크기:</strong> ${(file.size / 1024).toFixed(2)} KB
        `;
        orderUploadBtn.disabled = false;
    }
}

// 주문서 업로드 처리
async function handleOrderUpload() {
    if (!hasMasterData) {
        showStatus('먼저 자재마스터를 업로드해주세요.', 'error', orderUploadStatus);
        return;
    }

    const file = orderFileInput.files[0];
    if (!file) {
        showStatus('파일을 선택해주세요.', 'error', orderUploadStatus);
        return;
    }

    showLoading(true);
    orderUploadBtn.disabled = true;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/uploadOrder', {
            method: 'POST',
            body: formData
        });

        // 응답 상태 확인
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

        const data = await response.json();

        if (data.Success) {
            currentSessionId = data.session_id;
            currentItems = data.matched_items;

            showStatus(
                `주문서 처리 완료: 매칭 ${data.matched_count}개, 미매칭 ${data.unmatched_count}개`, 
                'success', 
                orderUploadStatus
            );

            // 미매칭 아이템 표시
            if (data.unmatched_items && data.unmatched_items.length > 0) {
                orderUnmatched.style.display = 'block';
                orderUnmatched.innerHTML = `
                    <h3>매칭되지 않은 아이템:</h3>
                    <ul>
                        ${data.unmatched_items.map(item => 
                            `<li><strong>${item.partno}</strong> - ${item.name} (수량: ${item.quantity}) - ${item.reason}</li>`
                        ).join('')}
                    </ul>
                `;
            } else {
                orderUnmatched.style.display = 'none';
            }

            // 주문서 아이템 표시
            if (data.matched_items && Array.isArray(data.matched_items)) {
                displayOrderItems(data.matched_items);
            } else {
                displayOrderItems([]);
            }
            
            // 섹션 표시
            orderItemsSection.style.display = 'block';
            boxSection.style.display = 'block';
            simSection.style.display = 'block';
        } else {
            showStatus(`오류: ${data.Reason}`, 'error', orderUploadStatus);
        }
    } catch (error) {
        showStatus(`업로드 오류: ${error.message}`, 'error', orderUploadStatus);
    } finally {
        showLoading(false);
        orderUploadBtn.disabled = false;
    }
}

// 주문서 아이템 표시
function displayOrderItems(items) {
    // 안전 체크
    if (!items || !Array.isArray(items)) {
        orderItemsList.innerHTML = '<p>아이템 데이터가 없습니다.</p>';
        return;
    }
    
    if (items.length === 0) {
        orderItemsList.innerHTML = '<p>표시할 아이템이 없습니다.</p>';
        return;
    }

    orderItemsList.innerHTML = items.map((item, index) => {
        // 안전한 데이터 접근
        const whd = item.WHD || [0, 0, 0];
        const original = item.original || {};
        const partno = item.partno || 'N/A';
        const name = item.name || '이름 없음';
        const weight = item.weight || 0;
        const typeofItem = item.typeof || 'cube';
        const category = original.분류 || '기타';
        const orderQuantity = item.order_quantity || 1;
        
        return `
        <div class="item-card" data-index="${index}">
            <div class="item-info">
                <h4>${name}</h4>
                <p><strong>제품번호:</strong> ${partno}</p>
                <p><strong>주문 수량:</strong> ${orderQuantity}개</p>
                <p><strong>크기:</strong> ${whd[0].toFixed(1)} × ${whd[1].toFixed(1)} × ${whd[2].toFixed(1)} cm</p>
                <p><strong>무게:</strong> ${weight} kg | <strong>타입:</strong> ${typeofItem} | <strong>분류:</strong> ${category}</p>
            </div>
        </div>
        `;
    }).join('');
}

// 상태 메시지 표시 (개선된 버전)
function showStatus(message, type, targetElement = null) {
    const element = targetElement || uploadStatus;
    element.textContent = message;
    element.className = `status-message ${type}`;
    element.style.display = 'block';

    if (type === 'success') {
        setTimeout(() => {
            element.style.display = 'none';
        }, 5000);
    }
}

// 상세 보고서 표시
function displayDetailedReports(detailedReport) {
    const reportsList = document.getElementById('detailed-reports-list');
    
    if (detailedReport.reports && detailedReport.reports.length > 0) {
        reportsList.style.display = 'block';
        reportsList.innerHTML = `
            <h3>📄 상세 보고서 (레이어별 정보)</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; margin-top: 15px;">
                ${detailedReport.reports.map(report => {
                    const binName = report.bin_info.partno;
                    const reportUrl = `/api/reportHTML/${currentSessionId}/${binName}`;
                    const workInstructionUrl = `/api/workInstruction/${currentSessionId}/${binName}`;
                    return `
                        <div style="padding: 15px; background: #f8f9fa; border-radius: 6px; border: 1px solid #ddd;">
                            <h4>${binName}</h4>
                            <p style="color: #666; font-size: 0.9em;">레이어 수: ${report.layers.length}개</p>
                            <div style="display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap;">
                                <a href="${reportUrl}" target="_blank" class="btn btn-primary" style="display: inline-block; text-decoration: none; padding: 8px 15px; border-radius: 4px;">
                                    📊 상세 보고서
                                </a>
                                <a href="${workInstructionUrl}" target="_blank" class="btn btn-secondary" style="display: inline-block; text-decoration: none; padding: 8px 15px; border-radius: 4px; background: #28a745; color: white;">
                                    🖨️ 작업 지시서
                                </a>
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    }
}

