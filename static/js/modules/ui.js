/**
 * UI 업데이트 관련 모듈
 */

/**
 * 로딩 오버레이 표시/숨김
 */
export function showLoading(show) {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = show ? 'flex' : 'none';
    }
}

/**
 * 상태 메시지 표시
 */
export function showStatus(message, type, targetElement = null) {
    const element = targetElement || document.getElementById('upload-status');
    if (element) {
        element.textContent = message;
        element.className = `status-message ${type}`;
        element.style.display = 'block';

        if (type === 'success') {
            setTimeout(() => {
                element.style.display = 'none';
            }, 5000);
        }
    }
}

/**
 * 통계 표시
 */
export function displayStats(stats) {
    if (!stats) {
        const statsContent = document.getElementById('stats-content');
        if (statsContent) {
            statsContent.innerHTML = '<p>통계 데이터가 없습니다.</p>';
        }
        return;
    }

    const statsContent = document.getElementById('stats-content');
    if (!statsContent) return;

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
}

/**
 * 아이템 표시
 */
export function displayItems(items) {
    if (!items || !Array.isArray(items)) {
        const itemsList = document.getElementById('items-list');
        if (itemsList) {
            itemsList.innerHTML = '<p>아이템 데이터가 없습니다.</p>';
        }
        return;
    }

    const itemsList = document.getElementById('items-list');
    if (!itemsList) return;

    if (items.length === 0) {
        itemsList.innerHTML = '<p>표시할 아이템이 없습니다.</p>';
        return;
    }

    itemsList.innerHTML = items.map((item, index) => {
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

/**
 * 주문서 아이템 표시
 */
export function displayOrderItems(items) {
    if (!items || !Array.isArray(items)) {
        const orderItemsList = document.getElementById('order-items-list');
        if (orderItemsList) {
            orderItemsList.innerHTML = '<p>아이템 데이터가 없습니다.</p>';
        }
        return;
    }

    const orderItemsList = document.getElementById('order-items-list');
    if (!orderItemsList) return;

    if (items.length === 0) {
        orderItemsList.innerHTML = '<p>표시할 아이템이 없습니다.</p>';
        return;
    }

    orderItemsList.innerHTML = items.map((item, index) => {
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

/**
 * 시뮬레이션 결과 표시
 */
export function displayResults(data, currentSessionId) {
    const resultsStats = document.getElementById('results-stats');
    const resultsImages = document.getElementById('results-images');

    // 통계 표시
    if (data.result && data.result.bins && resultsStats) {
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
    if (resultsImages) {
        if (data.images && data.images.length > 0) {
            resultsImages.innerHTML = data.images.map((image, index) => {
                const encodedImage = encodeURIComponent(image);
                return `
                    <div class="result-image">
                        <img src="/api/image/${encodedImage}"
                             loading="lazy"
                             alt="패킹 결과 이미지 ${index + 1}"
                             onerror="this.onerror=null; this.src='data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'400\' height=\'300\'%3E%3Ctext x=\'50%25\' y=\'50%25\' text-anchor=\'middle\'%3E이미지를 불러올 수 없습니다%3C/text%3E%3C/svg%3E';">
                    </div>
                `;
            }).join('');
        } else {
            resultsImages.innerHTML = '<p>생성된 이미지가 없습니다.</p>';
        }
    }

    // 상세 보고서 표시
    if (data.detailed_report && data.detailed_report.reports) {
        displayDetailedReports(data.detailed_report, currentSessionId);
    }
}

/**
 * 상세 보고서 표시
 */
export function displayDetailedReports(detailedReport, currentSessionId) {
    const reportsList = document.getElementById('detailed-reports-list');
    if (!reportsList) return;

    if (detailedReport.reports && detailedReport.reports.length > 0) {
        reportsList.style.display = 'block';
        reportsList.innerHTML = `
            <h3>📄 상세 보고서 (레이어별 정보)</h3>
            <div class="reports-grid">
                ${detailedReport.reports.map(report => {
                    const binName = report.bin_info.partno;
                    const reportUrl = `/api/reportHTML/${currentSessionId}/${binName}`;
                    const workInstructionUrl = `/api/workInstruction/${currentSessionId}/${binName}`;
                    return `
                        <div class="report-card">
                            <h4>${binName}</h4>
                            <p class="report-meta">레이어 수: ${report.layers.length}개</p>
                            <div class="report-actions">
                                <a href="${reportUrl}" target="_blank" class="btn btn-primary">
                                    📊 상세 보고서
                                </a>
                                <a href="${workInstructionUrl}" target="_blank" class="btn btn-secondary btn-success">
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

/**
 * 섹션 표시/숨김
 */
export function showSection(sectionId, show = true) {
    const section = document.getElementById(sectionId);
    if (section) {
        section.style.display = show ? 'block' : 'none';
    }
}

/**
 * 스크롤 이동
 */
export function scrollToSection(sectionId) {
    const section = document.getElementById(sectionId);
    if (section) {
        section.scrollIntoView({ behavior: 'smooth' });
    }
}
